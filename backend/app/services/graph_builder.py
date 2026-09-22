import networkx as nx

from app.services.ingestion import (
    load_persons,
    load_vehicles,
    load_cdr,
    load_finance,
    load_fir,
    load_social,
    load_surveillance
)
from app.services.normalization import clean_cell


def _value(row, column):
    if column not in row.index:
        return None
    return clean_cell(row[column])


def build_criminal_network():

    G = nx.MultiDiGraph()

    # -----------------------------------------
    # PERSONS
    # -----------------------------------------

    persons = load_persons()

    for _, row in persons.iterrows():
        person_id = _value(row, "person_id")
        if not person_id:
            continue

        G.add_node(
            person_id,
            entity_type="person",
            name=_value(row, "name"),
            phone=_value(row, "phone"),
            home_city=_value(row, "home_city"),
            risk_group=_value(row, "risk_group")
        )

    # -----------------------------------------
    # VEHICLES
    # Person -> Vehicle
    # -----------------------------------------

    vehicles = load_vehicles()

    for _, row in vehicles.iterrows():
        vehicle_id = _value(row, "vehicle_no")
        person_id = _value(row, "person_id")
        if not vehicle_id or not person_id:
            continue

        G.add_node(
            vehicle_id,
            entity_type="vehicle",
            registered_city=_value(row, "registered_city"),
            vehicle_type=_value(row, "vehicle_type")
        )

        G.add_edge(
            person_id,
            vehicle_id,
            relationship="OWNS"
        )

    # -----------------------------------------
    # CALL RECORDS
    # Person -> Person
    # -----------------------------------------

    cdr = load_cdr()

    for _, row in cdr.iterrows():
        caller_id = _value(row, "caller_id")
        receiver_id = _value(row, "receiver_id")
        if not caller_id or not receiver_id:
            continue

        G.add_edge(
            caller_id,
            receiver_id,
            relationship="CALLED",
            timestamp=str(_value(row, "timestamp") or ""),
            duration=_value(row, "duration_sec"),
            call_type=_value(row, "call_type")
        )

    # -----------------------------------------
    # FINANCIAL TRANSACTIONS
    # Person -> Person
    # -----------------------------------------

    finance = load_finance()

    for _, row in finance.iterrows():
        sender_id = _value(row, "sender_id")
        receiver_id = _value(row, "receiver_id")
        if not sender_id or not receiver_id:
            continue

        G.add_edge(
            sender_id,
            receiver_id,
            relationship="TRANSFERRED_MONEY",
            amount=_value(row, "amount"),
            date=str(_value(row, "date") or "")
        )

    # -----------------------------------------
    # FIR RECORDS
    # Person -> Crime Event
    # -----------------------------------------

    fir = load_fir()

    for _, row in fir.iterrows():
        fir_id = _value(row, "fir_id")
        person_id = _value(row, "person_id")
        if not fir_id or not person_id:
            continue

        G.add_node(
            fir_id,
            entity_type="crime_event",
            crime=_value(row, "crime"),
            date=str(_value(row, "date") or ""),
            location=_value(row, "location")
        )

        G.add_edge(
            person_id,
            fir_id,
            relationship="INVOLVED_IN"
        )

    # -----------------------------------------
    # SOCIAL CONNECTIONS
    # Person -> Person
    # -----------------------------------------

    social = load_social()

    for _, row in social.iterrows():
        user_id = _value(row, "user_id")
        connected_user_id = _value(row, "connected_user_id")
        if not user_id or not connected_user_id:
            continue

        G.add_edge(
            user_id,
            connected_user_id,
            relationship=f"SOCIAL_{str(_value(row, 'interaction_type') or 'UNKNOWN').upper()}",
            date=str(_value(row, "date") or "")
        )

    # -----------------------------------------
    # SURVEILLANCE
    # Person -> Location/Event
    # -----------------------------------------

    surveillance = load_surveillance()

    for _, row in surveillance.iterrows():
        event_id = _value(row, "event_id")
        person_id = _value(row, "person_id")
        if not event_id or not person_id:
            continue

        G.add_node(
            event_id,
            entity_type="surveillance_event",
            location=_value(row, "location"),
            timestamp=str(_value(row, "timestamp") or ""),
            event_type=_value(row, "event_type")
        )

        G.add_edge(
            person_id,
            event_id,
            relationship="OBSERVED_AT"
        )

    return G