import os
import sys
import json

sys.path.append(
    os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            os.path.pardir,
            "hackathon"
        )
    )
)

import hackathon_app

def test_lambda_handler():

    event = {
        "path": "/hackathon/hackthenorth2023"
    }

    response = hackathon_app.lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200

    assert body["name"] == "Hack the North 2023"
    assert "Waterloo" in body["description"]
    assert len(body["prizes"]) >= 16