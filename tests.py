"""
TaskFlow — Test Suite
Run: pytest tests/ -v
"""
import pytest
from app import app, db, User, Workspace, WorkspaceMember, hash_pw


@pytest.fixture
def client():
    """Create a test Flask client with an in-memory database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-secret'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture
def auth_client(client):
    """A client that is already logged in as the demo user."""
    with app.app_context():
        u = User(username='testuser', email='test@test.com',
                 password=hash_pw('password123'), avatar='🧪')
        db.session.add(u)
        db.session.flush()
        ws = Workspace(name='Test WS', slug='test-ws', owner_id=u.id, avatar='🏢')
        db.session.add(ws)
        db.session.flush()
        db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=u.id, role='owner'))
        u.active_ws_id = ws.id
        db.session.commit()

    client.post('/login', data={'email': 'test@test.com', 'password': 'password123'})
    return client


# ── Health Check ──────────────────────────────────────────────

def test_health_endpoint(client):
    """Health check should return 200."""
    r = client.get('/health')
    assert r.status_code == 200
    data = r.get_json()
    assert data['status'] == 'ok'


# ── Auth ──────────────────────────────────────────────────────

def test_login_page_loads(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'Sign In' in r.data or b'TaskFlow' in r.data


def test_register_page_loads(client):
    r = client.get('/register')
    assert r.status_code == 200


def test_register_new_user(client):
    r = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert r.status_code == 200


def test_duplicate_email_rejected(client):
    """Registering with a duplicate email should show an error, not crash."""
    with app.app_context():
        u = User(username='existing', email='dup@test.com',
                 password=hash_pw('pass'), avatar='😎')
        db.session.add(u)
        db.session.commit()

    r = client.post('/register', data={
        'username': 'someone',
        'email': 'dup@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'already exists' in r.data or b'error' in r.data.lower()


def test_login_valid_credentials(client, auth_client):
    r = client.get('/dashboard', follow_redirects=True)
    # After auth_client sets up session, dashboard should be accessible
    assert r.status_code == 200


def test_login_invalid_credentials(client):
    r = client.post('/login', data={
        'email': 'nobody@test.com',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b'Invalid' in r.data or b'credentials' in r.data.lower()


def test_redirect_unauthenticated(client):
    """Unauthenticated requests to protected routes redirect to login."""
    for route in ['/dashboard', '/tasks', '/projects', '/analytics']:
        r = client.get(route)
        assert r.status_code == 302
        assert '/login' in r.headers.get('Location', '')


# ── Dashboard ─────────────────────────────────────────────────

def test_dashboard_loads(auth_client):
    r = auth_client.get('/dashboard')
    assert r.status_code == 200
    assert b'Dashboard' in r.data


# ── Tasks ─────────────────────────────────────────────────────

def test_tasks_page_loads(auth_client):
    r = auth_client.get('/tasks')
    assert r.status_code == 200


def test_create_task(auth_client):
    r = auth_client.post('/tasks/new', data={
        'title': 'Test Task',
        'priority': 'medium',
        'status': 'todo',
        'story_points': '3',
        'redirect': 'tasks'
    }, follow_redirects=True)
    assert r.status_code == 200


# ── Projects ──────────────────────────────────────────────────

def test_projects_page_loads(auth_client):
    r = auth_client.get('/projects')
    assert r.status_code == 200


def test_create_project(auth_client):
    r = auth_client.post('/projects/new', data={
        'name': 'Test Project',
        'description': 'A test project',
        'emoji': '📁',
        'color': '#4f46e5'
    }, follow_redirects=True)
    assert r.status_code == 200


# ── Analytics ─────────────────────────────────────────────────

def test_analytics_loads(auth_client):
    r = auth_client.get('/analytics')
    assert r.status_code == 200


# ── API ───────────────────────────────────────────────────────

def test_search_api(auth_client):
    r = auth_client.get('/api/search?q=test')
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_search_empty(auth_client):
    r = auth_client.get('/api/search?q=')
    assert r.status_code == 200
    assert r.get_json() == []
