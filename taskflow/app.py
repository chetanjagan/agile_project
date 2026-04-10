from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json, hashlib, secrets, random
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskflow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ══════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════

class Workspace(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    slug        = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    avatar      = db.Column(db.String(4), default='🏢')
    plan        = db.Column(db.String(20), default='free')
    created     = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    members     = db.relationship('WorkspaceMember', backref='workspace', lazy=True, cascade='all,delete')
    projects    = db.relationship('Project', backref='workspace', lazy=True, cascade='all,delete')
    invites     = db.relationship('WorkspaceInvite', backref='workspace', lazy=True, cascade='all,delete')

class WorkspaceMember(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role         = db.Column(db.String(20), default='member')  # owner/admin/member/viewer
    joined       = db.Column(db.DateTime, default=datetime.utcnow)
    user         = db.relationship('User', backref='workspace_memberships')

class WorkspaceInvite(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    email        = db.Column(db.String(120), nullable=False)
    role         = db.Column(db.String(20), default='member')
    token        = db.Column(db.String(64), unique=True, nullable=False)
    invited_by   = db.Column(db.Integer, db.ForeignKey('user.id'))
    created      = db.Column(db.DateTime, default=datetime.utcnow)
    accepted     = db.Column(db.Boolean, default=False)
    inviter      = db.relationship('User', backref='sent_invites')

class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password      = db.Column(db.String(256), nullable=False)
    avatar        = db.Column(db.String(2), default='😎')
    role          = db.Column(db.String(20), default='member')
    created       = db.Column(db.DateTime, default=datetime.utcnow)
    active_ws_id  = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=True)
    tasks         = db.relationship('Task', foreign_keys='Task.assignee_id', backref='assignee', lazy=True)
    created_tasks = db.relationship('Task', foreign_keys='Task.creator_id', backref='creator', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

class ProjectMember(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role       = db.Column(db.String(20), default='member')  # admin/member/viewer
    joined     = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='project_memberships')

class Project(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    description  = db.Column(db.Text)
    color        = db.Column(db.String(20), default='#6C63FF')
    emoji        = db.Column(db.String(4), default='📁')
    is_private   = db.Column(db.Boolean, default=False)
    created      = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id     = db.Column(db.Integer, db.ForeignKey('user.id'))
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'))
    owner        = db.relationship('User', backref='owned_projects')
    tasks        = db.relationship('Task', backref='project', lazy=True, cascade='all,delete')
    members      = db.relationship('ProjectMember', backref='project', lazy=True, cascade='all,delete')
    sprints      = db.relationship('Sprint', backref='project', lazy=True, cascade='all,delete')

class Task(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text)
    status       = db.Column(db.String(30), default='todo')
    priority     = db.Column(db.String(20), default='medium')
    deadline     = db.Column(db.DateTime)
    estimated_h  = db.Column(db.Float, default=0)
    logged_h     = db.Column(db.Float, default=0)
    progress     = db.Column(db.Integer, default=0)
    tags         = db.Column(db.String(300), default='')
    story_points = db.Column(db.Integer, default=1)
    created      = db.Column(db.DateTime, default=datetime.utcnow)
    updated      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project_id   = db.Column(db.Integer, db.ForeignKey('project.id'))
    assignee_id  = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator_id   = db.Column(db.Integer, db.ForeignKey('user.id'))
    comments     = db.relationship('Comment', backref='task', lazy=True, cascade='all,delete')
    activity     = db.relationship('Activity', backref='task', lazy=True, cascade='all,delete')
    subtasks     = db.relationship('Subtask', backref='task', lazy=True, cascade='all,delete')

class Subtask(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    title   = db.Column(db.String(200), nullable=False)
    done    = db.Column(db.Boolean, default=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))

class Comment(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    body    = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    author  = db.relationship('User', backref='comments')

class Activity(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    action  = db.Column(db.String(300))
    created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    actor   = db.relationship('User', backref='activities')

class Notification(db.Model):
    id      = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(300))
    read    = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    link    = db.Column(db.String(200))

class Sprint(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    goal       = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date   = db.Column(db.DateTime)
    status     = db.Column(db.String(20), default='planned')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    velocity   = db.Column(db.Integer, default=0)

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def hash_pw(pw):  return hashlib.sha256(pw.encode()).hexdigest()
def make_slug(s): return s.lower().replace(' ','-')[:40] + '-' + secrets.token_hex(3)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def active_workspace():
    u = current_user()
    if not u: return None
    if u.active_ws_id:
        ws = Workspace.query.get(u.active_ws_id)
        if ws: return ws
    ws = Workspace.query.filter_by(owner_id=u.id).first()
    if ws: u.active_ws_id = ws.id; db.session.commit()
    return ws

def get_ws_role(ws, user):
    m = WorkspaceMember.query.filter_by(workspace_id=ws.id, user_id=user.id).first()
    return m.role if m else None

def get_proj_role(project, user):
    if project.owner_id == user.id: return 'admin'
    m = ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first()
    return m.role if m else None

def user_can_see_project(project, user):
    ws = active_workspace()
    if not ws or not get_ws_role(ws, user): return False
    if project.workspace_id != ws.id: return False
    if project.owner_id == user.id: return True
    if not project.is_private: return True
    return get_proj_role(project, user) is not None

def visible_projects(user):
    ws = active_workspace()
    if not ws: return []
    return [p for p in ws.projects if user_can_see_project(p, user)]

def ws_members_list(ws):
    return [wm.user for wm in ws.members]

def notify(user_id, message, link=''):
    db.session.add(Notification(message=message, user_id=user_id, link=link))

def log_activity(task_id, action):
    u = current_user()
    if u: db.session.add(Activity(action=action, user_id=u.id, task_id=task_id))

def make_workspace_for(user, name=None):
    ws = Workspace(name=name or f"{user.username}'s Workspace",
                   slug=make_slug(user.username), owner_id=user.id, avatar='🏢')
    db.session.add(ws); db.session.flush()
    db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role='owner'))
    user.active_ws_id = ws.id
    return ws

# ══════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(email=request.form['email']).first()
        if u and u.password == hash_pw(request.form['password']):
            session['user_id'] = u.id
            token = session.pop('pending_invite', None)
            if token: return redirect(url_for('accept_invite', token=token))
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    invite_token = request.args.get('invite') or session.get('pending_invite')
    invite = WorkspaceInvite.query.filter_by(token=invite_token, accepted=False).first() if invite_token else None
    if request.method == 'POST':
        avatars = ['😎','🦄','🐉','🦊','🐺','🦁','🐯','🦅','🦋','🌟','⚡','🔥','🌊','🍀','🎭']
        u = User(username=request.form['username'], email=request.form['email'],
                 password=hash_pw(request.form['password']), avatar=random.choice(avatars))
        db.session.add(u); db.session.flush()
        if invite and invite.email == u.email:
            ws = invite.workspace
            db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=u.id, role=invite.role))
            invite.accepted = True; u.active_ws_id = ws.id
        else:
            make_workspace_for(u)
        db.session.commit(); session['user_id'] = u.id
        return redirect(url_for('dashboard'))
    return render_template('register.html', invite=invite)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# ══════════════════════════════════════════════════════
#  WORKSPACES
# ══════════════════════════════════════════════════════

@app.route('/workspaces')
@login_required
def workspaces():
    u = current_user()
    my_ws = [wm.workspace for wm in u.workspace_memberships]
    return render_template('workspaces.html', user=u, workspaces=my_ws)

@app.route('/workspaces/new', methods=['POST'])
@login_required
def new_workspace():
    u = current_user()
    ws = Workspace(name=request.form['name'], slug=make_slug(request.form['name']),
                   description=request.form.get('description',''),
                   avatar=request.form.get('avatar','🏢'), owner_id=u.id)
    db.session.add(ws); db.session.flush()
    db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=u.id, role='owner'))
    u.active_ws_id = ws.id; db.session.commit()
    flash(f'Workspace "{ws.name}" created!', 'success')
    return redirect(url_for('workspace_settings', wid=ws.id))

@app.route('/workspaces/<int:wid>/switch')
@login_required
def switch_workspace(wid):
    u = current_user(); ws = Workspace.query.get_or_404(wid)
    if get_ws_role(ws, u): u.active_ws_id = wid; db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/workspaces/<int:wid>/settings', methods=['GET','POST'])
@login_required
def workspace_settings(wid):
    u = current_user(); ws = Workspace.query.get_or_404(wid)
    role = get_ws_role(ws, u)
    if not role: return redirect(url_for('dashboard'))
    if request.method == 'POST' and role in ('owner','admin'):
        ws.name = request.form.get('name', ws.name)
        ws.description = request.form.get('description', ws.description)
        ws.avatar = request.form.get('avatar', ws.avatar)
        db.session.commit(); flash('Workspace updated!', 'success')
    members = WorkspaceMember.query.filter_by(workspace_id=wid).all()
    invites = WorkspaceInvite.query.filter_by(workspace_id=wid, accepted=False).all()
    return render_template('workspace_settings.html', user=u, ws=ws, role=role,
                           members=members, invites=invites)

@app.route('/workspaces/<int:wid>/invite', methods=['POST'])
@login_required
def invite_to_workspace(wid):
    u = current_user(); ws = Workspace.query.get_or_404(wid)
    if get_ws_role(ws, u) not in ('owner','admin'):
        flash('Only admins can invite.', 'error')
        return redirect(url_for('workspace_settings', wid=wid))
    email = request.form['email'].strip().lower()
    role  = request.form.get('role','member')
    existing = User.query.filter_by(email=email).first()
    if existing and get_ws_role(ws, existing):
        flash(f'{email} is already a member.', 'error')
        return redirect(url_for('workspace_settings', wid=wid))
    old = WorkspaceInvite.query.filter_by(workspace_id=wid, email=email, accepted=False).first()
    if old: db.session.delete(old)
    inv = WorkspaceInvite(workspace_id=wid, email=email, role=role,
                          invited_by=u.id, token=secrets.token_urlsafe(32))
    db.session.add(inv); db.session.commit()
    if existing:
        db.session.add(WorkspaceMember(workspace_id=wid, user_id=existing.id, role=role))
        inv.accepted = True
        notify(existing.id, f'{u.username} added you to "{ws.name}"', f'/workspaces/{wid}/switch')
        db.session.commit()
        flash(f'{existing.username} added to the workspace!', 'success')
    else:
        link = url_for('accept_invite', token=inv.token, _external=True)
        flash(f'Invite link for {email}: {link}', 'success')
    return redirect(url_for('workspace_settings', wid=wid))

@app.route('/invite/<token>')
def accept_invite(token):
    inv = WorkspaceInvite.query.filter_by(token=token, accepted=False).first_or_404()
    u   = current_user()
    if not u:
        session['pending_invite'] = token
        return redirect(url_for('register', invite=token))
    if u.email != inv.email:
        flash('This invite is for a different email.', 'error')
        return redirect(url_for('dashboard'))
    ws = inv.workspace
    if not get_ws_role(ws, u):
        db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=u.id, role=inv.role))
    inv.accepted = True; u.active_ws_id = ws.id; db.session.commit()
    flash(f'Welcome to "{ws.name}"!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/workspaces/<int:wid>/members/<int:uid>/role', methods=['POST'])
@login_required
def change_ws_role(wid, uid):
    u = current_user(); ws = Workspace.query.get_or_404(wid)
    if get_ws_role(ws, u) not in ('owner','admin'): return jsonify({'ok':False}), 403
    m = WorkspaceMember.query.filter_by(workspace_id=wid, user_id=uid).first_or_404()
    new_role = request.get_json().get('role','member')
    if ws.owner_id == uid: return jsonify({'ok':False,'msg':'Cannot change owner'}), 400
    m.role = new_role; db.session.commit()
    return jsonify({'ok': True})

@app.route('/workspaces/<int:wid>/members/<int:uid>/remove', methods=['POST'])
@login_required
def remove_ws_member(wid, uid):
    u = current_user(); ws = Workspace.query.get_or_404(wid)
    if get_ws_role(ws, u) not in ('owner','admin') and u.id != uid:
        return redirect(url_for('workspace_settings', wid=wid))
    m = WorkspaceMember.query.filter_by(workspace_id=wid, user_id=uid).first()
    if m: db.session.delete(m); db.session.commit()
    return redirect(url_for('workspace_settings', wid=wid))

@app.route('/workspaces/<int:wid>/invites/<int:iid>/revoke', methods=['POST'])
@login_required
def revoke_invite(wid, iid):
    inv = WorkspaceInvite.query.get_or_404(iid)
    db.session.delete(inv); db.session.commit()
    flash('Invite revoked.', 'success')
    return redirect(url_for('workspace_settings', wid=wid))

# ══════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    u = current_user(); ws = active_workspace()
    all_tasks = Task.query.filter_by(assignee_id=u.id).all()
    overdue  = [t for t in all_tasks if t.deadline and t.deadline < datetime.utcnow() and t.status!='done']
    due_soon = [t for t in all_tasks if t.deadline and datetime.utcnow() < t.deadline <= datetime.utcnow()+timedelta(days=3) and t.status!='done']
    projs    = visible_projects(u)
    stats    = dict(total=len(all_tasks),
                    done=len([t for t in all_tasks if t.status=='done']),
                    in_progress=len([t for t in all_tasks if t.status=='in_progress']),
                    overdue=len(overdue))
    return render_template('dashboard.html', user=u, ws=ws,
                           my_tasks=sorted(all_tasks, key=lambda t: t.deadline or datetime.max)[:8],
                           projects=projs, stats=stats, overdue=overdue[:5], due_soon=due_soon[:5])

# ══════════════════════════════════════════════════════
#  PROJECTS
# ══════════════════════════════════════════════════════

@app.route('/projects')
@login_required
def projects():
    u = current_user(); ws = active_workspace()
    return render_template('projects.html', user=u, ws=ws, projects=visible_projects(u))

@app.route('/projects/new', methods=['POST'])
@login_required
def new_project():
    u = current_user(); ws = active_workspace()
    if not ws: flash('Create a workspace first.', 'error'); return redirect(url_for('workspaces'))
    p = Project(name=request.form['name'], description=request.form.get('description',''),
                color=request.form.get('color','#6C63FF'), emoji=request.form.get('emoji','📁'),
                is_private='is_private' in request.form, owner_id=u.id, workspace_id=ws.id)
    db.session.add(p); db.session.flush()
    db.session.add(ProjectMember(project_id=p.id, user_id=u.id, role='admin'))
    db.session.commit()
    return redirect(url_for('project_detail', pid=p.id))

@app.route('/projects/<int:pid>')
@login_required
def project_detail(pid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if not user_can_see_project(p, u):
        flash('You do not have access to this project.', 'error')
        return redirect(url_for('projects'))
    ws = active_workspace()
    ws_users = ws_members_list(ws) if ws else []
    proj_member_ids = {pm.user_id for pm in p.members}
    kanban = {s: [t for t in p.tasks if t.status==s] for s in ['todo','in_progress','review','done']}
    return render_template('project.html', user=u, project=p, tasks=p.tasks, kanban=kanban,
                           proj_role=get_proj_role(p, u), ws_users=ws_users,
                           proj_member_ids=proj_member_ids, members=ws_users)

@app.route('/projects/<int:pid>/settings', methods=['GET','POST'])
@login_required
def project_settings(pid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if not user_can_see_project(p, u): return redirect(url_for('projects'))
    if get_proj_role(p, u) != 'admin':
        flash('Only project admins can change settings.', 'error')
        return redirect(url_for('project_detail', pid=pid))
    if request.method == 'POST':
        p.name = request.form.get('name', p.name)
        p.description = request.form.get('description', p.description)
        p.color = request.form.get('color', p.color)
        p.emoji = request.form.get('emoji', p.emoji)
        p.is_private = 'is_private' in request.form
        db.session.commit(); flash('Project updated!', 'success')
    ws = active_workspace()
    ws_users = ws_members_list(ws) if ws else []
    proj_members = ProjectMember.query.filter_by(project_id=pid).all()
    return render_template('project_settings.html', user=u, project=p,
                           proj_role=get_proj_role(p, u), ws_users=ws_users, proj_members=proj_members)

@app.route('/projects/<int:pid>/members/add', methods=['POST'])
@login_required
def add_project_member(pid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if get_proj_role(p, u) != 'admin':
        flash('Only admins can add members.', 'error'); return redirect(url_for('project_detail', pid=pid))
    uid = int(request.form['user_id']); role = request.form.get('role','member')
    existing = ProjectMember.query.filter_by(project_id=pid, user_id=uid).first()
    if existing: existing.role = role
    else: db.session.add(ProjectMember(project_id=pid, user_id=uid, role=role))
    target = User.query.get(uid)
    if target: notify(uid, f'{u.username} added you to project "{p.name}"', f'/projects/{pid}')
    db.session.commit(); flash('Member added!', 'success')
    return redirect(url_for('project_settings', pid=pid))

@app.route('/projects/<int:pid>/members/<int:uid>/remove', methods=['POST'])
@login_required
def remove_project_member(pid, uid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if get_proj_role(p, u) != 'admin' and u.id != uid:
        flash('Not allowed.', 'error'); return redirect(url_for('project_settings', pid=pid))
    m = ProjectMember.query.filter_by(project_id=pid, user_id=uid).first()
    if m: db.session.delete(m); db.session.commit()
    flash('Member removed.', 'success')
    return redirect(url_for('project_settings', pid=pid))

@app.route('/projects/<int:pid>/members/<int:uid>/role', methods=['POST'])
@login_required
def change_project_role(pid, uid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if get_proj_role(p, u) != 'admin': return jsonify({'ok':False}), 403
    m = ProjectMember.query.filter_by(project_id=pid, user_id=uid).first()
    if m: m.role = request.get_json().get('role','member'); db.session.commit()
    return jsonify({'ok': True})

@app.route('/projects/<int:pid>/delete', methods=['POST'])
@login_required
def delete_project(pid):
    u = current_user(); p = Project.query.get_or_404(pid)
    if p.owner_id != u.id: flash('Only the owner can delete.', 'error'); return redirect(url_for('project_detail', pid=pid))
    db.session.delete(p); db.session.commit()
    return redirect(url_for('projects'))

# ══════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════

@app.route('/tasks')
@login_required
def tasks():
    u = current_user(); ws = active_workspace()
    ws_users = ws_members_list(ws) if ws else []
    return render_template('tasks.html', user=u, ws=ws,
                           tasks=Task.query.filter_by(assignee_id=u.id).order_by(Task.deadline).all(),
                           projects=visible_projects(u), members=ws_users)

@app.route('/tasks/new', methods=['POST'])
@login_required
def new_task():
    u = current_user()
    deadline = None
    if request.form.get('deadline'):
        try: deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')
        except: pass
    t = Task(title=request.form['title'], description=request.form.get('description',''),
             status=request.form.get('status','todo'), priority=request.form.get('priority','medium'),
             deadline=deadline, estimated_h=float(request.form.get('estimated_h') or 0),
             story_points=int(request.form.get('story_points') or 1),
             tags=request.form.get('tags',''), project_id=request.form.get('project_id') or None,
             assignee_id=int(request.form.get('assignee_id') or u.id), creator_id=u.id)
    db.session.add(t); db.session.flush()
    log_activity(t.id, 'created this task')
    if t.assignee_id and t.assignee_id != u.id:
        notify(t.assignee_id, f'{u.username} assigned you "{t.title}"', f'/tasks/{t.id}')
    db.session.commit()
    redir = request.form.get('redirect','tasks')
    if redir.startswith('project_'): return redirect(url_for('project_detail', pid=redir.split('_')[1]))
    return redirect(url_for('tasks'))

@app.route('/tasks/<int:tid>')
@login_required
def task_detail(tid):
    u = current_user(); t = Task.query.get_or_404(tid); ws = active_workspace()
    return render_template('task_detail.html', user=u, task=t,
                           members=ws_members_list(ws) if ws else [],
                           projects=visible_projects(u))

@app.route('/tasks/<int:tid>/update', methods=['POST'])
@login_required
def update_task(tid):
    t = Task.query.get_or_404(tid)
    if request.is_json:
        data = request.get_json()
        for k, v in data.items():
            if hasattr(t, k): setattr(t, k, v)
        t.updated = datetime.utcnow(); db.session.commit()
        if 'status' in data: log_activity(t.id, f"moved to {data['status'].replace('_',' ')}"); db.session.commit()
        return jsonify({'ok': True})
    deadline = None
    if request.form.get('deadline'):
        try: deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')
        except: pass
    t.title=request.form.get('title',t.title); t.description=request.form.get('description',t.description)
    t.status=request.form.get('status',t.status); t.priority=request.form.get('priority',t.priority)
    t.deadline=deadline or t.deadline
    t.estimated_h=float(request.form.get('estimated_h') or t.estimated_h)
    t.logged_h=float(request.form.get('logged_h') or t.logged_h)
    t.progress=int(request.form.get('progress') or t.progress)
    t.tags=request.form.get('tags',t.tags); t.story_points=int(request.form.get('story_points') or t.story_points)
    t.assignee_id=request.form.get('assignee_id') or t.assignee_id
    t.project_id=request.form.get('project_id') or t.project_id
    t.updated=datetime.utcnow(); db.session.commit()
    log_activity(t.id,'updated this task'); db.session.commit()
    return redirect(url_for('task_detail', tid=tid))

@app.route('/tasks/<int:tid>/delete', methods=['POST'])
@login_required
def delete_task(tid):
    t = Task.query.get_or_404(tid); pid = t.project_id
    db.session.delete(t); db.session.commit()
    return redirect(url_for('project_detail', pid=pid) if pid else url_for('tasks'))

@app.route('/tasks/<int:tid>/comment', methods=['POST'])
@login_required
def add_comment(tid):
    u = current_user()
    db.session.add(Comment(body=request.form['body'], user_id=u.id, task_id=tid))
    log_activity(tid, f"commented: {request.form['body'][:60]}"); db.session.commit()
    return redirect(url_for('task_detail', tid=tid))

@app.route('/tasks/<int:tid>/subtask', methods=['POST'])
@login_required
def add_subtask(tid):
    s = Subtask(title=request.form['title'], task_id=tid)
    db.session.add(s); db.session.commit()
    return jsonify({'id': s.id, 'title': s.title, 'done': s.done})

@app.route('/subtask/<int:sid>/toggle', methods=['POST'])
@login_required
def toggle_subtask(sid):
    s = Subtask.query.get_or_404(sid); s.done = not s.done; db.session.commit()
    t = Task.query.get(s.task_id)
    if t.subtasks: t.progress = int(100 * sum(1 for x in t.subtasks if x.done) / len(t.subtasks)); db.session.commit()
    return jsonify({'done': s.done, 'progress': t.progress})

@app.route('/tasks/<int:tid>/log_time', methods=['POST'])
@login_required
def log_time(tid):
    t = Task.query.get_or_404(tid); hours = float(request.form.get('hours', 0))
    t.logged_h += hours; db.session.commit()
    log_activity(tid, f"logged {hours}h"); db.session.commit()
    return jsonify({'logged_h': t.logged_h})

# ══════════════════════════════════════════════════════
#  SPRINTS
# ══════════════════════════════════════════════════════

@app.route('/projects/<int:pid>/sprint/new', methods=['POST'])
@login_required
def new_sprint(pid):
    db.session.add(Sprint(name=request.form['name'], goal=request.form.get('goal',''),
                          start_date=datetime.strptime(request.form['start_date'],'%Y-%m-%d'),
                          end_date=datetime.strptime(request.form['end_date'],'%Y-%m-%d'),
                          project_id=pid))
    db.session.commit(); return redirect(url_for('project_detail', pid=pid))

@app.route('/sprint/<int:sid>/activate', methods=['POST'])
@login_required
def activate_sprint(sid):
    s = Sprint.query.get_or_404(sid)
    Sprint.query.filter_by(project_id=s.project_id, status='active').update({'status':'completed'})
    s.status = 'active'; db.session.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════

@app.route('/analytics')
@login_required
def analytics():
    u = current_user(); ws = active_workspace()
    all_tasks = Task.query.filter_by(assignee_id=u.id).all()
    projs = visible_projects(u)
    status_data   = {s: len([t for t in all_tasks if t.status==s]) for s in ['todo','in_progress','review','done']}
    priority_data = {p: len([t for t in all_tasks if t.priority==p]) for p in ['low','medium','high','critical']}
    timeline = [{'day': (datetime.utcnow().date()-timedelta(days=6-i)).strftime('%a'),
                 'count': len([t for t in all_tasks if t.updated and t.updated.date()==(datetime.utcnow().date()-timedelta(days=6-i)) and t.status=='done'])}
                for i in range(7)]
    sp_data = [{'name': p.name, 'points': sum(t.story_points for t in p.tasks if t.status=='done')} for p in projs]
    return render_template('analytics.html', user=u, ws=ws,
        status_data=json.dumps(status_data), priority_data=json.dumps(priority_data),
        timeline=json.dumps(timeline), sp_data=json.dumps(sp_data),
        total_est=sum(t.estimated_h for t in all_tasks), total_log=sum(t.logged_h for t in all_tasks),
        total_tasks=len(all_tasks), done_tasks=status_data['done'],
        velocity=sum(t.story_points for t in all_tasks if t.status=='done'))

# ══════════════════════════════════════════════════════
#  API
# ══════════════════════════════════════════════════════

@app.route('/api/tasks/status', methods=['POST'])
@login_required
def api_update_status():
    data = request.get_json(); t = Task.query.get_or_404(data['task_id'])
    old = t.status; t.status = data['status']; t.updated = datetime.utcnow(); db.session.commit()
    log_activity(t.id, f"moved from {old} to {t.status}"); db.session.commit()
    return jsonify({'ok': True})

@app.route('/api/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifs_read():
    Notification.query.filter_by(user_id=current_user().id).update({'read': True})
    db.session.commit(); return jsonify({'ok': True})

@app.route('/api/search')
@login_required
def search():
    u = current_user(); q = request.args.get('q','').strip()
    if not q: return jsonify([])
    tasks = Task.query.filter(Task.assignee_id==u.id, Task.title.ilike(f'%{q}%')).limit(8).all()
    return jsonify([{'id':t.id,'title':t.title,'status':t.status,'priority':t.priority} for t in tasks])

# ══════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    u = current_user()
    if request.method == 'POST':
        u.username = request.form.get('username', u.username)
        u.avatar   = request.form.get('avatar', u.avatar)
        db.session.commit(); flash('Profile updated!', 'success')
    return render_template('profile.html', user=u)

# ══════════════════════════════════════════════════════
#  CONTEXT PROCESSOR
# ══════════════════════════════════════════════════════

@app.context_processor
def inject_globals():
    u = current_user()
    notifs=[]; unread_notifs=0; overdue_count=0; ws=None; my_workspaces=[]
    if u:
        notifs        = Notification.query.filter_by(user_id=u.id).order_by(Notification.created.desc()).limit(8).all()
        unread_notifs = Notification.query.filter_by(user_id=u.id, read=False).count()
        overdue_count = Task.query.filter(Task.assignee_id==u.id,
                                          Task.deadline < datetime.utcnow(),
                                          Task.status!='done').count()
        ws           = active_workspace()
        my_workspaces = [wm.workspace for wm in u.workspace_memberships]
    return dict(now=datetime.utcnow(), notifs=notifs, unread_notifs=unread_notifs,
                overdue_count=overdue_count, ws=ws, my_workspaces=my_workspaces)

# ══════════════════════════════════════════════════════
#  SEED & INIT
# ══════════════════════════════════════════════════════

def seed_demo():
    if User.query.count() > 0: return
    u = User(username='demo', email='demo@taskflow.com', password=hash_pw('demo123'), avatar='🚀', role='admin')
    db.session.add(u); db.session.flush()
    ws = make_workspace_for(u, 'TaskFlow HQ')
    ws.avatar='⚡'; ws.description='Main workspace for the TaskFlow team'; db.session.flush()
    u2 = User(username='alice', email='alice@taskflow.com', password=hash_pw('demo123'), avatar='🦄')
    db.session.add(u2); db.session.flush()
    db.session.add(WorkspaceMember(workspace_id=ws.id, user_id=u2.id, role='member'))
    u2.active_ws_id = ws.id
    p1 = Project(name='TaskFlow Dev', description='Building the app itself', color='#6C63FF', emoji='⚡',
                 is_private=False, owner_id=u.id, workspace_id=ws.id)
    p2 = Project(name='Marketing Q2', description='Q2 campaigns – private', color='#FF6584', emoji='📣',
                 is_private=True, owner_id=u.id, workspace_id=ws.id)
    db.session.add_all([p1, p2]); db.session.flush()
    db.session.add(ProjectMember(project_id=p1.id, user_id=u.id, role='admin'))
    db.session.add(ProjectMember(project_id=p1.id, user_id=u2.id, role='member'))
    db.session.add(ProjectMember(project_id=p2.id, user_id=u.id, role='admin'))
    tasks_data = [
        ('Design login UI','done','high',3,p1.id,u.id),
        ('Set up Flask app','done','critical',5,p1.id,u.id),
        ('Build Kanban board','in_progress','high',8,p1.id,u2.id),
        ('Add analytics page','in_progress','medium',5,p1.id,u.id),
        ('Write unit tests','todo','medium',3,p1.id,u2.id),
        ('Deploy to prod','todo','high',5,p1.id,u.id),
        ('SEO optimization','review','medium',3,p2.id,u.id),
        ('Email campaign','todo','low',2,p2.id,u.id),
    ]
    for title,status,priority,sp,pid,aid in tasks_data:
        db.session.add(Task(title=title,status=status,priority=priority,story_points=sp,
                            project_id=pid,assignee_id=aid,creator_id=u.id,
                            deadline=datetime.utcnow()+timedelta(days=sp),
                            estimated_h=sp*2,logged_h=sp*1.2 if status=='done' else sp*0.5,
                            progress=100 if status=='done' else (50 if status=='in_progress' else 0),
                            tags='backend,flask' if pid==p1.id else 'marketing'))
    db.session.add(Sprint(name='Sprint 1',goal='Core features',project_id=p1.id,
                          start_date=datetime.utcnow(),end_date=datetime.utcnow()+timedelta(days=14),
                          status='active'))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_demo()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
