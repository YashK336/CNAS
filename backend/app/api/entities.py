from fastapi import APIRouter, HTTPException

from app.services.ingestion import (
    dataframe_records,
    load_persons,
    load_vehicles,
    load_entity_mapping
)


router = APIRouter(
    prefix="/entities",
    tags=["Entities"]
)


# ------------------------------------------------
# PERSONS
# ------------------------------------------------

@router.get("/persons")
def get_persons():

    df = load_persons()
    data = dataframe_records(df)

    return {
        "total": len(data),
        "data": data
    }


@router.get("/persons/{person_id}")
def get_person(person_id: str):

    df = load_persons()

    person = df[
        df["person_id"].astype(str) == person_id
    ]

    if person.empty:
        raise HTTPException(
            status_code=404,
            detail="Person not found"
        )

    records = dataframe_records(person)
    return records[0]


# ------------------------------------------------
# VEHICLES
# ------------------------------------------------

@router.get("/vehicles")
def get_vehicles():

    df = load_vehicles()
    data = dataframe_records(df)

    return {
        "total": len(data),
        "data": data
    }


# ------------------------------------------------
# PHONES
# ------------------------------------------------

@router.get("/phones")
def get_phones():

    df = load_entity_mapping()

    phones = df[
        df["entity_type"] == "phone"
    ]
    data = dataframe_records(phones)

    return {
        "total": len(data),
        "data": data
    }


# ------------------------------------------------
# LOCATIONS
# ------------------------------------------------

@router.get("/locations")
def get_locations():

    persons = load_persons()

    locations = (
        persons[["home_city"]]
        .drop_duplicates()
        .rename(
            columns={
                "home_city": "location"
            }
        )
    )
    data = dataframe_records(locations)

    return {
        "total": len(data),
        "data": data
    }