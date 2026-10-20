from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.diagnostico_cumplimiento.api.dependencies import get_diagnostic_service
from agents.diagnostico_cumplimiento.api.routes import router
from agents.diagnostico_cumplimiento.api.service import DiagnosticService


def make_client():
    service = DiagnosticService()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_diagnostic_service] = lambda: service
    return TestClient(app)


def start(client, workers=5):
    response = client.post('/api/v1/diagnostics', json={'worker_count': workers})
    assert response.status_code == 201, response.text
    return response.json()


def answer(client, state, value):
    question = state['next_question']
    response = client.post(
        f"/api/v1/diagnostics/{state['diagnosis_id']}/answers",
        json={
            'requirement_id': question['requirement_id'],
            'question_id': question['question_id'],
            'answer': value,
            'revision': state['revision'],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def restart(client, state, requirement_id):
    return client.post(
        f"/api/v1/diagnostics/{state['diagnosis_id']}/requirements/{requirement_id}/restart",
        json={'revision': state['revision']},
    )


def test_restart_completed_requirement_returns_to_first_pending_without_losing_others():
    client = make_client()
    state = start(client)
    requirement_two = state['requirements'][1]['requirement_id']
    while state['next_question']['requirement_number'] < 5:
        state = answer(client, state, False)
    original_revision = state['revision']
    before = {r['requirement_id']: r['status'] for r in state['requirements']}
    assert before[requirement_two] == 'completed'
    assert state['progress']['completed_requirements'] == 4

    response = restart(client, state, requirement_two)
    assert response.status_code == 200, response.text
    state = response.json()
    assert state['revision'] == original_revision + 1
    assert state['next_question']['requirement_number'] == 2
    assert state['progress']['completed_requirements'] == 3
    for r in state['requirements']:
        if r['requirement_number'] in (1, 3, 4):
            assert r['status'] == 'completed'

    while state['next_question']['requirement_number'] == 2:
        state = answer(client, state, False)
    assert state['next_question']['requirement_number'] == 5
    assert state['progress']['completed_requirements'] == 4
    assert restart(client, {'diagnosis_id': state['diagnosis_id'], 'revision': original_revision}, requirement_two).status_code == 409


def test_restart_partial_requirement_and_dependency_recalculation():
    client = make_client()
    state = start(client)
    first_requirement = state['next_question']['requirement_id']
    state = answer(client, state, True)
    assert state['next_question']['requirement_id'] == first_requirement
    assert state['requirements'][0]['status'] == 'in_progress'
    old_question = state['next_question']

    response = restart(client, state, first_requirement)
    assert response.status_code == 200, response.text
    state = response.json()
    assert state['next_question']['question_id'] != old_question['question_id']
    assert state['requirements'][0]['status'] == 'pending'
    assert state['progress']['completed_requirements'] == 0

    stale = client.post(
        f"/api/v1/diagnostics/{state['diagnosis_id']}/answers",
        json={
            'requirement_id': old_question['requirement_id'],
            'question_id': old_question['question_id'],
            'answer': True,
            'revision': state['revision'] - 1,
        },
    )
    assert stale.status_code == 409
    state = answer(client, state, False)
    assert state['next_question']['requirement_number'] == 2
    assert state['requirements'][0]['status'] == 'completed'


def test_get_state_and_reject_unknown_or_unstarted_requirement():
    client = make_client()
    state = start(client, workers=11)
    uri = f"/api/v1/diagnostics/{state['diagnosis_id']}"
    snapshot = client.get(uri)
    assert snapshot.status_code == 200
    assert len(snapshot.json()['requirements']) == 21
    assert snapshot.json()['revision'] == 0
    assert restart(client, state, state['requirements'][1]['requirement_id']).status_code == 409
    assert restart(client, state, 'unknown').status_code == 409
    assert client.get('/api/v1/diagnostics/unknown').status_code == 404
