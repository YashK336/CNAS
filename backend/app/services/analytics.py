import statistics

import networkx as nx
import community as community_louvain

GRAPH_PROPAGATION_MAX = 10


def _normalize_graph_seeds(graph_seeds: list[str] | None) -> list[str] | None:
    if not graph_seeds:
        return None
    seeds = [seed.strip() for seed in graph_seeds if seed and seed.strip()]
    return seeds or None


def _load_personalized_pagerank_scores(graph_seeds: list[str]) -> dict[str, float]:
    try:
        from app.services.neo4j_gds_analytics import calculate_personalized_pagerank

        result = calculate_personalized_pagerank(
            graph_seeds,
            refresh_projection=False,
        )
        return {
            str(row["entity_id"]): float(row["personalized_pagerank"])
            for row in result.get("data", [])
            if row.get("entity_id") is not None
        }
    except Exception:
        return {}


def _graph_propagation_contribution(personalized_pagerank: float | None) -> float:
    if personalized_pagerank is None:
        return 0.0
    return min(GRAPH_PROPAGATION_MAX, round(personalized_pagerank * 100, 2))

def _empty_scores(G):
    return {node: 0.0 for node in G.nodes()}


def _safe_degree_centrality(G):
    if G is None or G.number_of_nodes() == 0:
        return {}
    try:
        return nx.degree_centrality(G)
    except Exception:
        return _empty_scores(G)


def _safe_betweenness(G):
    if G is None or G.number_of_nodes() == 0:
        return {}
    try:
        return nx.betweenness_centrality(G, normalized=True)
    except Exception:
        return _empty_scores(G)


def _safe_pagerank(G):
    if G is None or G.number_of_nodes() == 0:
        return {}
    try:
        return nx.pagerank(G)
    except Exception:
        try:
            from networkx.algorithms.link_analysis.pagerank_alg import (
                _pagerank_python,
            )

            return _pagerank_python(G)
        except Exception:
            return _empty_scores(G)


def calculate_centrality(G):
    degree = _safe_degree_centrality(G)
    betweenness = _safe_betweenness(G)
    pagerank = _safe_pagerank(G)

    results = []

    for node_id, data in G.nodes(data=True):
        results.append({
            "entity_id": node_id,
            "name": data.get("name"),
            "degree_centrality": round(degree.get(node_id, 0), 4),
            "betweenness_centrality": round(
                betweenness.get(node_id, 0),
                4,
            ),
            "pagerank": round(pagerank.get(node_id, 0), 4),
        })

    results.sort(key=lambda item: item["pagerank"], reverse=True)
    return results


def network_statistics(G):
    counts = {
        "person": 0,
        "vehicle": 0,
        "crime_event": 0,
        "surveillance_event": 0,
    }

    for _, data in G.nodes(data=True):
        entity_type = data.get("entity_type")
        if entity_type in counts:
            counts[entity_type] += 1

    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "people": counts["person"],
        "vehicles": counts["vehicle"],
        "crime_events": counts["crime_event"],
        "surveillance_events": counts["surveillance_event"],
    }


def detect_communities(G):
    if G.number_of_nodes() == 0:
        return []

    undirected = G.to_undirected()
    communities = nx.community.greedy_modularity_communities(undirected)
    results = []

    for index, community in enumerate(communities, start=1):
        members = []
        for node_id in community:
            data = G.nodes.get(node_id, {})
            members.append({
                "entity_id": node_id,
                "name": data.get("name"),
            })

        results.append({
            "community_id": index,
            "size": len(members),
            "members": members,
        })

    return results


def find_connection(G, source_id, target_id):
    if source_id not in G or target_id not in G:
        return {
            "found": False,
            "message": "Source or target entity not found",
        }

    try:
        path = nx.shortest_path(G, source_id, target_id)
    except nx.NetworkXNoPath:
        return {
            "found": False,
            "message": "No path between the selected entities",
        }

    nodes = []
    relationships = []

    for node_id in path:
        data = G.nodes.get(node_id, {})
        nodes.append({
            "entity_id": node_id,
            "entity_type": data.get("entity_type"),
            "name": data.get("name"),
            "location": data.get("home_city")
            or data.get("location")
            or data.get("registered_city"),
        })

    for index in range(len(path) - 1):
        source = path[index]
        target = path[index + 1]
        edge_data = G.get_edge_data(source, target) or {}
        first_edge = next(iter(edge_data.values()), {}) if edge_data else {}
        relationships.append({
            "source": source,
            "target": target,
            "relationship": first_edge.get("relationship"),
        })

    return {
        "found": True,
        "source": source_id,
        "target": target_id,
        "degrees_of_separation": len(path) - 1,
        "nodes": nodes,
        "relationships": relationships,
    }


def calculate_risk(G, graph_seeds: list[str] | None = None):
    """
    Explainable rule-based risk scoring.

    Scoring is based on observable network activity:
    - Communication activity
    - Financial activity
    - Social activity
    - FIR involvement
    - Surveillance activity
    - Network bridge role
    - Network influence

    When graph seed person IDs are supplied, a bounded Personalized PageRank
    contribution is added without replacing the existing rule signals.
    """
    seeds = _normalize_graph_seeds(graph_seeds)
    graph_scores = _load_personalized_pagerank_scores(seeds) if seeds else {}

    centrality = calculate_centrality(G)

    centrality_map = {
        item["entity_id"]: item
        for item in centrality
    }

    results = []

    for node_id, data in G.nodes(data=True):

        if data.get("entity_type") != "person":
            continue

        # -----------------------------
        # Count relationship activity
        # -----------------------------

        communication = 0
        financial = 0
        social = 0
        fir = 0
        surveillance = 0

        for source, target, edge_data in G.edges(
            node_id,
            data=True
        ):
            relationship = edge_data.get("relationship", "")

            if relationship == "CALLED":
                communication += 1

            elif relationship == "TRANSFERRED_MONEY":
                financial += 1

            elif relationship.startswith("SOCIAL_"):
                social += 1

            elif relationship == "INVOLVED_IN":
                target_data = G.nodes.get(target, {})

                if target_data.get("entity_type") == "crime_event":
                    fir += 1

                elif target_data.get("entity_type") == "surveillance_event":
                    surveillance += 1

        # Incoming relationships also matter
        for source, target, edge_data in G.in_edges(
            node_id,
            data=True
        ):
            relationship = edge_data.get("relationship", "")

            if relationship == "CALLED":
                communication += 1

            elif relationship == "TRANSFERRED_MONEY":
                financial += 1

            elif relationship.startswith("SOCIAL_"):
                social += 1

        # -----------------------------
        # Network metrics
        # -----------------------------

        metrics = centrality_map.get(
            node_id,
            {
                "degree_centrality": 0,
                "betweenness_centrality": 0,
                "pagerank": 0
            }
        )

        degree = metrics["degree_centrality"]
        betweenness = metrics["betweenness_centrality"]
        pagerank = metrics["pagerank"]

        # -----------------------------
        # Rule scoring
        # -----------------------------

        communication_score = min(20, communication * 2)
        financial_score = min(20, financial * 4)
        social_score = min(15, social * 3)
        fir_score = min(20, fir * 10)
        surveillance_score = min(10, surveillance * 2)

        bridge_score = min(
            10,
            round(betweenness * 100, 2)
        )

        influence_score = min(
            5,
            round(pagerank * 100, 2)
        )

        base_score = round(
            communication_score
            + financial_score
            + social_score
            + fir_score
            + surveillance_score
            + bridge_score
            + influence_score
        )

        personalized_pagerank = None
        graph_contribution = 0.0
        if seeds:
            personalized_pagerank = graph_scores.get(str(node_id))
            graph_contribution = _graph_propagation_contribution(personalized_pagerank)

        total_score = min(100, round(base_score + graph_contribution))

        # -----------------------------
        # Risk band
        # -----------------------------

        if total_score >= 75:
            risk_level = "CRITICAL"
        elif total_score >= 50:
            risk_level = "HIGH"
        elif total_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # -----------------------------
        # Explainable signals
        # -----------------------------

        signals = {
            "social_activity": round(social_score / 15, 2),
            "communication_activity": round(
                communication_score / 20,
                2
            ),
            "financial_activity": round(
                financial_score / 20,
                2
            ),
            "fir_involvement": round(
                fir_score / 20,
                2
            ),
            "network_bridge_role": round(
                bridge_score / 10,
                2
            ),
            "network_influence": round(
                influence_score / 5,
                2
            ),
            "surveillance_activity": round(
                surveillance_score / 10,
                2
            )
        }

        if seeds:
            signals["graph_propagation"] = round(
                graph_contribution / GRAPH_PROPAGATION_MAX,
                2,
            )

        profile = {
            "entity_id": node_id,
            "name": data.get("name"),
            "risk_score": total_score,
            "risk_level": risk_level,
            "signals": signals,
            "raw_activity": {
                "communications": communication,
                "financial_transactions": financial,
                "social_interactions": social,
                "fir_involvement": fir,
                "surveillance_events": surveillance
            },
            "scoring_method": "rules_v1+graph_propagation" if seeds else "rules_v1",
        }

        if seeds:
            profile["graph_seeds"] = seeds
            profile["personalized_pagerank"] = (
                round(float(personalized_pagerank), 4)
                if personalized_pagerank is not None
                else None
            )
            profile["graph_contribution"] = graph_contribution

        results.append(profile)

    results.sort(
        key=lambda x: x["risk_score"],
        reverse=True
    )

    return results


def calculate_risk_scores(G):
    return calculate_risk(G)


def detect_communities(G):
    """
    Detect communities among PERSON nodes.

    Uses the undirected projection of the criminal network
    because community structure is based on connectivity,
    not relationship direction.
    """

    person_nodes = [
        node
        for node, data in G.nodes(data=True)
        if data.get("entity_type") == "person"
    ]

    person_graph = G.subgraph(person_nodes).to_undirected()

    if person_graph.number_of_nodes() == 0:
        return {
            "total_communities": 0,
            "communities": []
        }

    partition = community_louvain.best_partition(
        person_graph,
        random_state=42
    )

    communities = {}

    for person_id, community_id in partition.items():
        communities.setdefault(
            community_id,
            []
        ).append(person_id)

    results = []

    for community_id, members in communities.items():

        member_details = []

        for person_id in members:
            data = G.nodes[person_id]

            member_details.append({
                "entity_id": person_id,
                "name": data.get("name")
            })

        results.append({
            "community_id": community_id,
            "size": len(members),
            "members": member_details
        })

    results.sort(
        key=lambda x: x["size"],
        reverse=True
    )

    # Give communities stable display IDs
    for index, community in enumerate(results, start=1):
        community["community_id"] = index

    return {
        "total_communities": len(results),
        "communities": results
    }


# ---------------------------------------------------------------------------
# Behavioral anomaly detection (explainable statistical baseline)
# ---------------------------------------------------------------------------
#
# This is not a criminality classifier. It flags people whose *observed*
# activity is unusually high relative to other people in the current graph.
# FIR involvement is excluded: that signal belongs to the risk engine.

ANOMALY_FEATURE_WEIGHTS = {
    "communication": 0.25,
    "financial": 0.30,
    "social": 0.20,
    "surveillance": 0.25,
}

# Modified z of 3.5 is the Iglewicz–Hoaglin robust outlier cutoff. Values at
# or above it saturate the 0–1 feature score.
ANOMALY_Z_CAP = 3.5

# A feature must reach this 0–1 score before it earns an explanation. Below
# that the deviation is not treated as a meaningful investigative indicator.
ANOMALY_REASON_THRESHOLD = 0.5

ANOMALY_REASONS = {
    "communication": (
        "Communication activity is unusually high compared with the network."
    ),
    "financial": (
        "Financial transaction activity is unusually high compared with peers."
    ),
    "social": (
        "Social interaction activity is unusually high compared with the network."
    ),
    "surveillance": (
        "Surveillance activity is unusually frequent compared with the network."
    ),
}


def _anomaly_level(score):
    if score >= 75:
        return "EXTREME"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "ELEVATED"
    return "NORMAL"


def _median(values):
    if not values:
        return 0.0
    return float(statistics.median(values))


def _mad(values, median_value):
    """Median absolute deviation. Zero when every value equals the median."""
    if not values:
        return 0.0
    return float(statistics.median([abs(value - median_value) for value in values]))


def _high_side_feature_score(value, values):
    """
    Normalized 0–1 score that rises only when `value` is unusually *high*.

    Primary formula (robust modified z-score):

        z = 0.6745 * (x - median) / MAD
        score = clip(z / 3.5, 0, 1)

    0.6745 scales MAD onto the same unit as a standard deviation for a
    normal distribution. Negative z (at or below the median) maps to 0:
    low activity is not an anomaly under this engine.

    Fallback when MAD is 0 (no spread around the median):

        if max == median: score = 0  (no one is unusual)
        else: score = clip((x - median) / (max - median), 0, 1)
    """
    if not values:
        return 0.0

    median_value = _median(values)
    spread = _mad(values, median_value)
    deviation = value - median_value

    if deviation <= 0:
        return 0.0

    if spread > 0:
        modified_z = 0.6745 * deviation / spread
        return round(min(1.0, max(0.0, modified_z / ANOMALY_Z_CAP)), 4)

    ceiling = max(values) - median_value
    if ceiling <= 0:
        return 0.0

    return round(min(1.0, max(0.0, deviation / ceiling)), 4)


def _person_activity_counts(G, node_id):
    """
    Observable behavioral counts for one person.

    Communication / financial / social count both directions (the person
    placed or received the activity). Surveillance counts outgoing links
    to surveillance_event nodes. The current dataset stores those as
    OBSERVED_AT; INVOLVED_IN to a surveillance_event is also counted if
    present. INVOLVED_IN to a crime_event (FIR) is ignored.
    """
    communication = 0
    financial = 0
    social = 0
    surveillance = 0

    for _source, target, edge_data in G.edges(node_id, data=True):
        relationship = edge_data.get("relationship", "") or ""

        if relationship == "CALLED":
            communication += 1
        elif relationship == "TRANSFERRED_MONEY":
            financial += 1
        elif relationship.startswith("SOCIAL_"):
            social += 1
        elif relationship in ("OBSERVED_AT", "INVOLVED_IN"):
            target_type = G.nodes.get(target, {}).get("entity_type")
            if target_type == "surveillance_event":
                surveillance += 1

    if hasattr(G, "in_edges"):
        for _source, _target, edge_data in G.in_edges(node_id, data=True):
            relationship = edge_data.get("relationship", "") or ""

            if relationship == "CALLED":
                communication += 1
            elif relationship == "TRANSFERRED_MONEY":
                financial += 1
            elif relationship.startswith("SOCIAL_"):
                social += 1

    total_activity = communication + financial + social + surveillance

    return {
        "communication": communication,
        "financial": financial,
        "social": social,
        "surveillance": surveillance,
        "total_activity": total_activity,
    }


def calculate_anomalies(G):
    """
    Identify people whose observed activity is unusually high compared with
    other people in this graph.

    Returns a list of anomaly profiles, sorted by anomaly_score descending.
    Empty, all-zero, single-person and missing-attribute graphs return
    well-defined scores (0) rather than raising.
    """
    if G is None or G.number_of_nodes() == 0:
        return []

    people = [
        (node_id, data)
        for node_id, data in G.nodes(data=True)
        if data.get("entity_type") == "person"
    ]

    if not people:
        return []

    activities = {
        node_id: _person_activity_counts(G, node_id)
        for node_id, _data in people
    }

    columns = {
        feature: [activities[node_id][feature] for node_id, _data in people]
        for feature in ANOMALY_FEATURE_WEIGHTS
    }

    # A feature with no observed activity anywhere cannot be compared and
    # is dropped so remaining weights still sum to 1.
    available = [
        feature
        for feature, values in columns.items()
        if max(values) > 0
    ]

    results = []

    for node_id, data in people:
        activity = activities[node_id]

        feature_scores = {
            feature: _high_side_feature_score(
                activity[feature],
                columns[feature],
            )
            for feature in ANOMALY_FEATURE_WEIGHTS
        }

        if available:
            weight_total = sum(
                ANOMALY_FEATURE_WEIGHTS[feature] for feature in available
            )
            combined = sum(
                feature_scores[feature]
                * (ANOMALY_FEATURE_WEIGHTS[feature] / weight_total)
                for feature in available
            )
        else:
            combined = 0.0

        anomaly_score = int(round(min(100, max(0, combined * 100))))
        anomaly_level = _anomaly_level(anomaly_score)

        reasons = []
        if anomaly_level != "NORMAL":
            for feature, score in feature_scores.items():
                if score >= ANOMALY_REASON_THRESHOLD:
                    reasons.append(ANOMALY_REASONS[feature])

            if not reasons:
                strongest = max(feature_scores, key=feature_scores.get)
                if feature_scores[strongest] > 0:
                    reasons.append(ANOMALY_REASONS[strongest])

        results.append({
            "entity_id": node_id,
            "name": data.get("name"),
            "anomaly_score": anomaly_score,
            "anomaly_level": anomaly_level,
            "feature_scores": {
                "communication": feature_scores["communication"],
                "financial": feature_scores["financial"],
                "social": feature_scores["social"],
                "surveillance": feature_scores["surveillance"],
            },
            "activity": {
                "communications": activity["communication"],
                "financial_transactions": activity["financial"],
                "social_interactions": activity["social"],
                "surveillance_events": activity["surveillance"],
            },
            "reasons": reasons,
            "method": "robust_statistical_v1",
        })

    results.sort(
        key=lambda item: (-item["anomaly_score"], str(item["entity_id"]))
    )
    return results


def anomaly_distribution(profiles):
    distribution = {
        "NORMAL": 0,
        "ELEVATED": 0,
        "HIGH": 0,
        "EXTREME": 0,
    }

    for profile in profiles:
        level = profile.get("anomaly_level")
        if level in distribution:
            distribution[level] += 1

    return {
        "total_people": len(profiles),
        "distribution": distribution,
    } 