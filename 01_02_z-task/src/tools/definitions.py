tools = [
    {
        "type": "function",
        "name": "get_suspects",
        "description": "Load suspect list from transport_workers.json",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_power_plants",
        "description": "Fetch list of power plants and coordinates from findhim_locations.json on HUB",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_person_locations",
        "description": "Fetch seen locations (latitude/longitude) for a person from /api/location",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "First name"},
                "surname": {"type": "string", "description": "Last name"},
            },
            "required": ["name", "surname"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "find_nearest_power_plant",
        "description": "Find the nearest power plant to any provided person location using Haversine distance",
        "parameters": {
            "type": "object",
            "properties": {
                "personLocations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number"},
                            "lon": {"type": "number"},
                        },
                        "required": ["lat", "lon"],
                        "additionalProperties": False,
                    },
                },
                "powerPlants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "lat": {"type": "number"},
                            "lon": {"type": "number"},
                        },
                        "required": ["code", "lat", "lon"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["personLocations", "powerPlants"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_access_level",
        "description": "Fetch access level for a person from /api/accesslevel",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "First name"},
                "surname": {"type": "string", "description": "Last name"},
                "birthYear": {
                    "type": "integer",
                    "description": "Birth year as integer, e.g. 1987",
                },
            },
            "required": ["name", "surname", "birthYear"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "submit_findhim_answer",
        "description": "Submit final findhim answer to /verify",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "surname": {"type": "string"},
                "accessLevel": {"type": "integer"},
                "powerPlant": {
                    "type": "string",
                    "description": "Power plant code in format PWR0000PL",
                },
            },
            "required": ["name", "surname", "accessLevel", "powerPlant"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
