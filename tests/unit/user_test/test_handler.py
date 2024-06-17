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
            "user"
        )
    )
)

import user_app

def test_lambda_handler():

    event = {
        "path": "/user/justinbax"
    }

    response = user_app.lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200

    assert body["username"] == "justinbax"
    assert body["name"] == "Justin Bax"
    assert len(body["projects"]) >= 4
    assert any([project["did_win"] for project in body["projects"]])
    assert body["followers"] >= 1
    assert len(body["hackathons"]) >= 4
    assert "mcgill-physics-hackathon-2023" in body["hackathons"]
    assert body["links"]["github"] == "https://github.com/justinbax"