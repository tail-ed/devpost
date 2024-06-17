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
            "project"
        )
    )
)

import project_app

def test_lambda_handler():

    event = {
        "path": "/project/singulario"
    }

    response = project_app.lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200

    assert body["title"] == "Singulario"
    assert body["link"] == "singulario"
    assert "n-body simulation" in body["description"]
    assert len(body["built_with"]) >= 3
    assert len(body["app_links"]) >= 2
    assert body["submitted_to"][0] == "McGill Physics Hackathon 2023"
    assert len(body["created_by"]) >= 3
    assert body["likes"] >= 15
    assert len(body["prizes"]) >= 2