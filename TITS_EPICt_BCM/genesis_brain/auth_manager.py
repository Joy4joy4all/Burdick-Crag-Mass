# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
GIBUSH CORE - AUTHENTICATION MANAGER
=====================================
User authentication, team management, and access control.

MIT Engineering Standard:
- bcrypt password hashing
- Session token management  
- Role-based access control (RBAC)
- Audit logging

Emerald Entities LLC — GIBUSH Systems
"""

import json
import hashlib
import secrets
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
class UserRole(Enum):
    """Role-based access control levels"""
    ADMIN = "admin"              # Full system access
    FOREMAN = "foreman"    # BCM foreman/lead — test_batch management, feature control
    PROJECT_LEAD = "project_lead"  # Can create projects, manage team
    RESEARCHER = "researcher"     # Can run tests, view data
    VIEWER = "viewer"            # Read-only access
    

@dataclass
class User:
    """User account"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    team_id: str
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True
    display_name: str = ""
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['role'] = self.role.value
        return d
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'User':
        d['role'] = UserRole(d['role'])
        return cls(**d)


@dataclass
class Team:
    """Research team/organization"""
    team_id: str
    team_name: str
    organization: str
    created_at: str
    admin_user_id: str
    project_ids: List[str] = field(default_factory=list)
    member_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'Team':
        return cls(**d)


@dataclass
class Session:
    """Active user session"""
    session_id: str
    user_id: str
    team_id: str
    token: str
    created_at: str
    expires_at: str
    ip_address: str = ""
    
    @property
    def is_expired(self) -> bool:
        return datetime.fromisoformat(self.expires_at) < datetime.now()


class AuthManager:
    """
    Manages authentication, users, teams, and sessions.
    
    Storage Structure:
    .gibush/
    â”œâ”€â”€ auth/
    â”‚   â”œâ”€â”€ users.json
    â”‚   â”œâ”€â”€ teams.json
    â”‚   â”œâ”€â”€ sessions.json
    â”‚   â””â”€â”€ audit_log.json
    """
    
    SESSION_DURATION_HOURS = 24
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path.home() / ".gibush" / "auth"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self.teams_file = self.data_dir / "teams.json"
        self.sessions_file = self.data_dir / "sessions.json"
        self.audit_file = self.data_dir / "audit_log.json"
        
        self._load_data()
    
    def _load_data(self):
        """Load all data from files"""
        # Users
        if self.users_file.exists():
            with open(self.users_file) as f:
                data = json.load(f)
                self.users = {uid: User.from_dict(u) for uid, u in data.items()}
        else:
            self.users: Dict[str, User] = {}
        
        # Teams
        if self.teams_file.exists():
            with open(self.teams_file) as f:
                data = json.load(f)
                self.teams = {tid: Team.from_dict(t) for tid, t in data.items()}
        else:
            self.teams: Dict[str, Team] = {}
        
        # Sessions
        if self.sessions_file.exists():
            with open(self.sessions_file) as f:
                data = json.load(f)
                self.sessions = {sid: Session(**s) for sid, s in data.items()}
        else:
            self.sessions: Dict[str, Session] = {}
    
    def _save_users(self):
        """Save users to file"""
        with open(self.users_file, 'w') as f:
            json.dump({uid: u.to_dict() for uid, u in self.users.items()}, f, indent=2)
    
    def _save_teams(self):
        """Save teams to file"""
        with open(self.teams_file, 'w') as f:
            json.dump({tid: t.to_dict() for tid, t in self.teams.items()}, f, indent=2)
    
    def _save_sessions(self):
        """Save sessions to file"""
        with open(self.sessions_file, 'w') as f:
            json.dump({sid: asdict(s) for sid, s in self.sessions.items()}, f, indent=2)
    
    def _audit_log(self, action: str, user_id: str, details: str = ""):
        """Write to audit log"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details
        }
        
        log = []
        if self.audit_file.exists():
            with open(self.audit_file) as f:
                log = json.load(f)
        
        log.append(entry)
        
        # Keep last 10000 entries
        if len(log) > 10000:
            log = log[-10000:]
        
        with open(self.audit_file, 'w') as f:
            json.dump(log, f, indent=2)
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate unique ID"""
        return f"{prefix}{secrets.token_hex(8)}"
    
    def _hash_password(self, password: str) -> str:
        """Hash password with PBKDF2"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"{salt}${hash_obj.hex()}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt, hash_hex = stored_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return hash_obj.hex() == hash_hex
        except ValueError:
            return False
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    
    def create_user(
        self, 
        username: str, 
        email: str, 
        password: str,
        role: UserRole = UserRole.RESEARCHER,
        team_id: str = "",
        display_name: str = ""
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Create new user account.
        
        Returns: (success, message, user)
        """
        # Validate
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters", None
        
        if not email or '@' not in email:
            return False, "Valid email required", None
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters", None
        
        # Check uniqueness
        for u in self.users.values():
            if u.username.lower() == username.lower():
                return False, "Username already exists", None
            if u.email.lower() == email.lower():
                return False, "Email already registered", None
        
        # Create user
        user_id = self._generate_id("USR_")
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            role=role,
            team_id=team_id,
            created_at=datetime.now().isoformat(),
            display_name=display_name or username
        )
        
        self.users[user_id] = user
        self._save_users()
        self._audit_log("USER_CREATED", user_id, f"username={username}")
        
        return True, "User created successfully", user
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[Session]]:
        """
        Authenticate user and create session.
        
        Returns: (success, message, session)
        """
        # Find user
        user = None
        for u in self.users.values():
            if u.username.lower() == username.lower() or u.email.lower() == username.lower():
                user = u
                break
        
        if not user:
            return False, "User not found", None
        
        if not user.is_active:
            return False, "Account is disabled", None
        
        if not self._verify_password(password, user.password_hash):
            self._audit_log("LOGIN_FAILED", user.user_id, "invalid password")
            return False, "Invalid password", None
        
        # Create session
        session_id = self._generate_id("SES_")
        token = secrets.token_urlsafe(32)
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            team_id=user.team_id,
            token=token,
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=self.SESSION_DURATION_HOURS)).isoformat()
        )
        
        self.sessions[session_id] = session
        self._save_sessions()
        
        # Update last login
        user.last_login = datetime.now().isoformat()
        self._save_users()
        
        self._audit_log("LOGIN_SUCCESS", user.user_id)
        
        return True, "Login successful", session
    
    def validate_session(self, token: str) -> Tuple[bool, Optional[User], Optional[Session]]:
        """
        Validate session token.
        
        Returns: (valid, user, session)
        """
        for session in self.sessions.values():
            if session.token == token:
                if session.is_expired:
                    return False, None, None
                
                user = self.users.get(session.user_id)
                if user and user.is_active:
                    return True, user, session
        
        return False, None, None
    
    def logout(self, token: str) -> bool:
        """End session"""
        for sid, session in list(self.sessions.items()):
            if session.token == token:
                self._audit_log("LOGOUT", session.user_id)
                del self.sessions[sid]
                self._save_sessions()
                return True
        return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        for u in self.users.values():
            if u.username.lower() == username.lower():
                return u
        return None
    
    # ========================================================================
    # TEAM MANAGEMENT
    # ========================================================================
    
    def create_team(
        self,
        team_name: str,
        organization: str,
        admin_user_id: str
    ) -> Tuple[bool, str, Optional[Team]]:
        """
        Create new team.
        
        Returns: (success, message, team)
        """
        if not team_name:
            return False, "Team name required", None
        
        # Check admin exists
        admin = self.users.get(admin_user_id)
        if not admin:
            return False, "Admin user not found", None
        
        team_id = self._generate_id("TEAM_")
        team = Team(
            team_id=team_id,
            team_name=team_name,
            organization=organization,
            created_at=datetime.now().isoformat(),
            admin_user_id=admin_user_id,
            member_ids=[admin_user_id]
        )
        
        self.teams[team_id] = team
        self._save_teams()
        
        # Update admin's team
        admin.team_id = team_id
        admin.role = UserRole.PROJECT_LEAD
        self._save_users()
        
        self._audit_log("TEAM_CREATED", admin_user_id, f"team={team_name}")
        
        return True, "Team created", team
    
    def add_team_member(self, team_id: str, user_id: str, added_by: str) -> Tuple[bool, str]:
        """Add user to team"""
        team = self.teams.get(team_id)
        if not team:
            return False, "Team not found"
        
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        if user_id in team.member_ids:
            return False, "User already in team"
        
        team.member_ids.append(user_id)
        user.team_id = team_id
        
        self._save_teams()
        self._save_users()
        self._audit_log("TEAM_MEMBER_ADDED", added_by, f"user={user_id} team={team_id}")
        
        return True, "Member added"
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        return self.teams.get(team_id)
    
    def get_team_members(self, team_id: str) -> List[User]:
        """Get all users in team"""
        team = self.teams.get(team_id)
        if not team:
            return []
        return [self.users[uid] for uid in team.member_ids if uid in self.users]
    
    # ========================================================================
    # PERMISSION CHECKS
    # ========================================================================
    
    def can_create_project(self, user: User) -> bool:
        """Check if user can create projects"""
        return user.role in [UserRole.ADMIN, UserRole.FOREMAN, UserRole.PROJECT_LEAD]
    
    def can_edit_project(self, user: User, project_id: str) -> bool:
        """Check if user can edit specific project"""
        if user.role in [UserRole.ADMIN, UserRole.FOREMAN]:
            return True
        
        team = self.teams.get(user.team_id)
        if team and project_id in team.project_ids:
            return user.role in [UserRole.PROJECT_LEAD, UserRole.RESEARCHER]
        
        return False
    
    def can_view_project(self, user: User, project_id: str) -> bool:
        """Check if user can view specific project"""
        if user.role in [UserRole.ADMIN, UserRole.FOREMAN]:
            return True
        
        team = self.teams.get(user.team_id)
        return team and project_id in team.project_ids
    
    def can_manage_test_batch(self, user: User) -> bool:
        """Check if user can access foreman terminal (test_batch management)."""
        return user.role in [UserRole.ADMIN, UserRole.FOREMAN]
    
    def can_toggle_features(self, user: User) -> bool:
        """Check if user can toggle feature flags per team."""
        return user.role in [UserRole.ADMIN, UserRole.FOREMAN]
    
    def can_export_evaluation(self, user: User) -> bool:
        """Check if user can export evaluation/AICA data."""
        return user.role in [UserRole.ADMIN, UserRole.FOREMAN]
    
    # ========================================================================
    # INITIALIZATION HELPERS
    # ========================================================================
    
    def setup_initial_admin(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """Setup initial admin account (first-run only)"""
        if self.users:
            return False, "System already initialized"
        
        success, msg, user = self.create_user(
            username=username,
            email=email,
            password=password,
            role=UserRole.ADMIN,
            display_name="System Administrator"
        )
        
        if success:
            self._audit_log("SYSTEM_INITIALIZED", user.user_id)
        
        return success, msg
    
    @property
    def is_initialized(self) -> bool:
        """Check if system has been initialized"""
        return len(self.users) > 0


# ============================================================================
# SINGLETON ACCESS
# ============================================================================

_auth_manager: Optional[AuthManager] = None

def get_auth_manager() -> AuthManager:
    """Get global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GIBUSH AUTH MANAGER TEST")
    print("=" * 60)
    
    auth = AuthManager(Path("./test_auth"))
    
    # Create admin
    if not auth.is_initialized:
        success, msg = auth.setup_initial_admin("admin", "admin@test.com", "adminpass123")
        print(f"Setup admin: {msg}")
    
    # Create team
    admin = auth.get_user_by_username("admin")
    if admin:
        success, msg, team = auth.create_team("MIT Research Team", "MIT", admin.user_id)
        print(f"Create team: {msg}")
    
    # Create researcher
    success, msg, researcher = auth.create_user(
        "researcher1", 
        "research@test.com", 
        "research123",
        UserRole.RESEARCHER
    )
    print(f"Create researcher: {msg}")
    
    # Login
    success, msg, session = auth.authenticate("admin", "adminpass123")
    print(f"Login: {msg}")
    if session:
        print(f"  Token: {session.token[:20]}...")
    
    # Validate
    if session:
        valid, user, _ = auth.validate_session(session.token)
        print(f"Validate session: valid={valid}, user={user.username if user else None}")
    
    print("\nAll users:")
    for u in auth.users.values():
        print(f"  {u.username} ({u.role.value})")
