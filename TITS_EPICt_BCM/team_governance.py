# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
TEAM GOVERNANCE — SHARED BACKBONE v2.0
========================================
Single source of truth for the TITS Triad Platform.

Hierarchy:
  Hub (University IT boots system)
    └── Institution (8 per hub — universities/colleges)
         └── Foreman (enrolls under institution, up to 3 sponsor a team)
              └── R&D Team (members, 6-digit PIN, projects, modules)
                   └── Projects (AISOS_SPINE, BCM_SUBSTRATE, ...)

Governance rules:
  - Foremans MUST enroll under an institution
  - Teams pick from listed foremans; up to 3 may SPONSOR a team
  - "Sponsored" = at least 1 foreman has claimed the team
  - Foremans can ONLY view teams they sponsor (cross-view blocked)
  - Inclusion accept requires originator to be on the project's team
  - Triad notes propagate to all 3 platforms (write once, read everywhere)
  - Footprints track navigation patterns for platform performance metrics

Imported by:
  - foreman_terminal.py   (Academia Hall)
  - validation_test_collector.py  (Research Validation Center)
  - gibush_main_CaaS.py     (Development Inclusion CaaS)
  - gibush_world_class_ehs.py  (Validation Emulsion AISOS)
  - gibush_boot.py / gibush_launcher.py  (Admin layer)

NO GUI in this file. Pure data layer + validation logic.

Location: C:/TITS/.../TITS_GIBUSH_AISOS_SPINE_EPIC/team_governance.py

Emerald Entities LLC — GIBUSH Systems
Stephen J. Burdick Sr. — Team GIBUSH
"""

import json
import hashlib
import secrets
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


# ============================================================================
# PATH RESOLUTION
# ============================================================================

def _resolve_governance_root() -> Path:
    _here = Path(__file__).resolve().parent
    for p in [_here] + list(_here.parents):
        candidate = p / "TITS_GIBUSH_AISOS_SPINE_EPIC"
        if candidate.is_dir():
            return candidate
        if p.name == "TITS_GIBUSH_AISOS_SPINE_EPIC":
            return p
    for drive in ["C:", "D:", "E:"]:
        for base in [
            Path(f"{drive}/TITS/TITS_GIBUSH_AISOS_SPINE/TITS_GIBUSH_AISOS_SPINE_EPIC"),
            Path(f"{drive}/TITS_GIBUSH_AISOS_SPINE_EPIC"),
        ]:
            if base.is_dir():
                return base
    fallback = _here / "governance_data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


GOVERNANCE_ROOT = _resolve_governance_root()
GOVERNANCE_FILE = GOVERNANCE_ROOT / "team_governance.json"
FOOTPRINT_FILE = GOVERNANCE_ROOT / "footprints.json"

print(f"[GOVERNANCE] Root: {GOVERNANCE_ROOT}")


# ============================================================================
# CONSTANTS
# ============================================================================

EPIC_HUBS = [
    "New England",
    "Northeast (Interior Northeast)",
    "Mid-Atlantic",
    "Southeast",
    "Great Lakes",
    "Midwest",
    "Southwest",
    "Desert and Pacific",
    "West",
    "National (NSF Direct)",
]

EPIC_PROGRAM_LEVELS = [
    "Regional (Baseline/Hub)",
    "National (Validation/Teams)",
    "Site/Node (Legacy)",
]

TRIAD_NOTE_CATEGORIES = [
    "GENERAL", "PIVOT", "TEST_RUN", "SAFETY",
    "KUDOS", "MILESTONE", "CONCERN",
]

MAX_SPONSORS_PER_TEAM = 3
ML_FOREMAN = "ML8"


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Institution:
    """University or college in an BCM Hub. ~8 per hub."""
    institution_id: str
    name: str
    hub_region: str = "New England"
    admin_name: str = ""
    admin_email: str = ""
    address: str = ""
    is_active: bool = True
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Institution":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class ForemanProfile:
    """BCM foreman. MUST enroll under an institution."""
    foreman_id: str
    name: str
    institution_id: str = ""
    hub_region: str = "New England"
    program_level: str = "National (Validation/Teams)"
    training_date: str = ""
    training_hub: str = ""
    specialization: str = ""
    email: str = ""
    bio: str = ""
    is_active: bool = True
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ForemanProfile":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class TeamMember:
    """A member of an R&D team."""
    name: str
    role: str = "EL"
    email: str = ""
    is_lead: bool = False
    is_admin: bool = False    # Admin sees all teams/data via toggle

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TeamMember":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class RDTeam:
    """R&D Team. Up to 3 foremans may SPONSOR."""
    team_id: str
    team_name: str
    pin_hash: str = ""
    pin_salt: str = ""
    sponsors: List[str] = field(default_factory=list)
    members: List[TeamMember] = field(default_factory=list)
    projects: List[str] = field(default_factory=list)
    institution: str = ""
    program_type: str = "Validation"
    hub_region: str = "New England"
    test_batch_id: str = ""
    is_active: bool = True
    created_at: str = ""
    last_activity: str = ""

    @property
    def is_sponsored(self) -> bool:
        return len(self.sponsors) > 0

    @property
    def sponsor_count(self) -> int:
        return len(self.sponsors)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["members"] = [m.to_dict() for m in self.members]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "RDTeam":
        members = [TeamMember.from_dict(m) for m in d.get("members", [])]
        valid = {k: v for k, v in d.items()
                 if k in cls.__dataclass_fields__ and k != "members"}
        return cls(members=members, **valid)


@dataclass
class TriadNote:
    """Foreman note → propagates to all 3 platforms."""
    note_id: str
    foreman_id: str
    foreman_name: str
    team_id: str
    content: str
    timestamp: str = ""
    category: str = "GENERAL"
    master_lens: str = "ML8"
    acknowledged_by: List[str] = field(default_factory=list)
    is_pinned: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TriadNote":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class Footprint:
    """Navigation event — tracks where users go. Eager eyes predict success."""
    user_name: str
    user_type: str          # "FOREMAN" or "TEAM_MEMBER"
    team_id: str
    platform: str           # "FUSION", "INCLUSION", "EMULSION"
    location: str           # Tab or file visited
    timestamp: str = ""
    session_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Footprint":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


# ============================================================================
# PIN MANAGEMENT
# ============================================================================

def _hash_pin(pin: str, salt: str = "") -> Tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    combined = f"{salt}:{pin}"
    hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return hashed, salt


def verify_pin(pin: str, pin_hash: str, pin_salt: str) -> bool:
    check_hash, _ = _hash_pin(pin, pin_salt)
    return secrets.compare_digest(check_hash, pin_hash)


# ============================================================================
# GOVERNANCE REGISTRY
# ============================================================================

class GovernanceRegistry:

    def __init__(self, filepath: Optional[Path] = None):
        self._filepath = filepath or GOVERNANCE_FILE
        self._footprint_file = self._filepath.parent / "footprints.json"
        self._institutions: Dict[str, Institution] = {}
        self._foremans: Dict[str, ForemanProfile] = {}
        self._teams: Dict[str, RDTeam] = {}
        self._triad_notes: List[TriadNote] = []
        self._footprints: List[Footprint] = []
        self._load()

    # ── Persistence ──

    def _load(self):
        if self._filepath.exists():
            try:
                data = json.loads(self._filepath.read_text(encoding='utf-8'))
                for k, v in data.get("institutions", {}).items():
                    self._institutions[k] = Institution.from_dict(v)
                for k, v in data.get("foremans", {}).items():
                    self._foremans[k] = ForemanProfile.from_dict(v)
                for k, v in data.get("teams", {}).items():
                    self._teams[k] = RDTeam.from_dict(v)
                for n in data.get("triad_notes", []):
                    self._triad_notes.append(TriadNote.from_dict(n))
                print(f"[GOVERNANCE] Loaded: {len(self._institutions)} inst, "
                      f"{len(self._foremans)} instr, "
                      f"{len(self._teams)} teams, {len(self._triad_notes)} notes")
            except Exception as e:
                print(f"[GOVERNANCE] Load error: {e}")
        else:
            print(f"[GOVERNANCE] No file — starting fresh")

        if self._footprint_file.exists():
            try:
                fp_data = json.loads(
                    self._footprint_file.read_text(encoding='utf-8'))
                for fp in fp_data.get("footprints", []):
                    self._footprints.append(Footprint.from_dict(fp))
            except Exception:
                pass

    def save(self):
        data = {
            "version": "2.0",
            "updated_at": datetime.now().isoformat(),
            "institutions": {k: v.to_dict()
                             for k, v in self._institutions.items()},
            "foremans": {k: v.to_dict()
                            for k, v in self._foremans.items()},
            "teams": {k: v.to_dict() for k, v in self._teams.items()},
            "triad_notes": [n.to_dict() for n in self._triad_notes],
        }
        self._filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self._filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_footprints(self):
        data = {
            "updated_at": datetime.now().isoformat(),
            "footprints": [fp.to_dict() for fp in self._footprints[-5000:]],
        }
        with open(self._footprint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ══════════════════════════════════════════════════════
    # INSTITUTION REGISTRY
    # ══════════════════════════════════════════════════════

    def register_institution(self, institution_id: str, name: str,
                             hub_region: str = "New England",
                             admin_name: str = "",
                             admin_email: str = "") -> Institution:
        iid = institution_id.upper()
        inst = Institution(
            institution_id=iid, name=name, hub_region=hub_region,
            admin_name=admin_name, admin_email=admin_email,
            created_at=datetime.now().isoformat(),
        )
        self._institutions[iid] = inst
        self.save()
        print(f"[GOVERNANCE] Registered institution: {name} ({iid})")
        return inst

    def get_institution(self, institution_id: str) -> Optional[Institution]:
        return self._institutions.get(institution_id.upper())

    def list_institutions(self, hub_region: str = "") -> List[Institution]:
        results = [i for i in self._institutions.values() if i.is_active]
        if hub_region:
            results = [i for i in results if i.hub_region == hub_region]
        return sorted(results, key=lambda i: i.name)

    # ══════════════════════════════════════════════════════
    # FOREMAN REGISTRY
    # ══════════════════════════════════════════════════════

    def register_foreman(self, name: str, institution_id: str,
                            hub_region: str = "New England",
                            program_level: str = "National (Validation/Teams)",
                            email: str = "", bio: str = "",
                            specialization: str = "",
                            training_date: str = "",
                            training_hub: str = "") -> Optional[ForemanProfile]:
        """Register foreman. MUST be under a valid institution."""
        iid = institution_id.upper()
        if iid not in self._institutions:
            print(f"[GOVERNANCE] BLOCKED: Institution {iid} not registered")
            return None

        count = len(self._foremans) + 1
        inst_id = f"INST-{count:03d}"
        while inst_id in self._foremans:
            count += 1
            inst_id = f"INST-{count:03d}"

        profile = ForemanProfile(
            foreman_id=inst_id, name=name, institution_id=iid,
            hub_region=hub_region, program_level=program_level,
            email=email, bio=bio, specialization=specialization,
            training_date=training_date, training_hub=training_hub,
            created_at=datetime.now().isoformat(),
        )
        self._foremans[inst_id] = profile
        self.save()
        print(f"[GOVERNANCE] Registered foreman: {name} ({inst_id}) "
              f"under {iid}")
        return profile

    def get_foreman(self, foreman_id: str) -> Optional[ForemanProfile]:
        return self._foremans.get(foreman_id)

    def list_foremans(self, institution_id: str = "",
                         active_only: bool = True) -> List[ForemanProfile]:
        results = list(self._foremans.values())
        if active_only:
            results = [i for i in results if i.is_active]
        if institution_id:
            iid = institution_id.upper()
            results = [i for i in results if i.institution_id == iid]
        return sorted(results, key=lambda i: i.name)

    def update_foreman_bio(self, foreman_id: str, bio: str) -> bool:
        inst = self._foremans.get(foreman_id)
        if not inst:
            return False
        inst.bio = bio
        self.save()
        return True

    def get_foreman_teams(self, foreman_id: str) -> List[RDTeam]:
        return [t for t in self._teams.values()
                if foreman_id in t.sponsors and t.is_active]

    # ══════════════════════════════════════════════════════
    # TEAM REGISTRY
    # ══════════════════════════════════════════════════════

    def register_team(self, team_id: str, team_name: str, pin: str,
                      members: Optional[List[Dict]] = None,
                      projects: Optional[List[str]] = None,
                      institution: str = "",
                      program_type: str = "Validation",
                      hub_region: str = "New England",
                      test_batch_id: str = "") -> RDTeam:
        if len(pin) < 4 or len(pin) > 8:
            raise ValueError("PIN must be 4-8 digits")
        if not pin.isdigit():
            raise ValueError("PIN must be numeric")

        pin_hash, pin_salt = _hash_pin(pin)
        member_objects = []
        if members:
            for m in members:
                if isinstance(m, dict):
                    member_objects.append(TeamMember.from_dict(m))
                elif isinstance(m, TeamMember):
                    member_objects.append(m)

        team = RDTeam(
            team_id=team_id.upper(), team_name=team_name,
            pin_hash=pin_hash, pin_salt=pin_salt,
            sponsors=[],
            members=member_objects,
            projects=[p.upper() for p in (projects or [])],
            institution=institution, program_type=program_type,
            hub_region=hub_region, test_batch_id=test_batch_id,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
        )
        self._teams[team.team_id] = team
        self.save()
        print(f"[GOVERNANCE] Registered team: {team_name} ({team.team_id}) "
              f"— UNSPONSORED")
        return team

    def get_team(self, team_id: str) -> Optional[RDTeam]:
        return self._teams.get(team_id.upper())

    def list_teams(self, active_only: bool = True) -> List[RDTeam]:
        results = list(self._teams.values())
        if active_only:
            results = [t for t in results if t.is_active]
        return sorted(results, key=lambda t: t.team_name)

    def authenticate_team(self, team_id: str, pin: str) -> bool:
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        result = verify_pin(pin, team.pin_hash, team.pin_salt)
        if result:
            team.last_activity = datetime.now().isoformat()
            self.save()
        return result

    def add_team_member(self, team_id: str, name: str, role: str = "EL",
                        email: str = "", is_lead: bool = False) -> bool:
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        team.members.append(TeamMember(
            name=name, role=role, email=email, is_lead=is_lead))
        self.save()
        return True

    def remove_team_member(self, team_id: str, name: str) -> bool:
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        before = len(team.members)
        team.members = [m for m in team.members if m.name != name]
        if len(team.members) < before:
            self.save()
            return True
        return False

    # ══════════════════════════════════════════════════════
    # SPONSORSHIP
    # ══════════════════════════════════════════════════════

    def sponsor_team(self, foreman_id: str,
                     team_id: str) -> Tuple[bool, str]:
        """Foreman claims a team. Max 3 sponsors per team."""
        team = self._teams.get(team_id.upper())
        if not team:
            return False, f"Team {team_id} not found"

        foreman = self._foremans.get(foreman_id)
        if not foreman:
            return False, f"Foreman {foreman_id} not found"

        if not foreman.institution_id:
            return False, (f"{foreman.name} has no institution")

        if foreman_id in team.sponsors:
            return True, f"Already sponsoring {team_id}"

        if len(team.sponsors) >= MAX_SPONSORS_PER_TEAM:
            return False, (f"{team_id} has {MAX_SPONSORS_PER_TEAM} sponsors (max)")

        team.sponsors.append(foreman_id)
        team.last_activity = datetime.now().isoformat()
        self.save()
        print(f"[GOVERNANCE] {foreman.name} sponsors {team_id} "
              f"({team.sponsor_count}/{MAX_SPONSORS_PER_TEAM})")
        return True, f"✓ {foreman.name} sponsors {team_id}"

    def unsponsor_team(self, foreman_id: str,
                       team_id: str) -> Tuple[bool, str]:
        team = self._teams.get(team_id.upper())
        if not team:
            return False, f"Team {team_id} not found"
        if foreman_id in team.sponsors:
            team.sponsors.remove(foreman_id)
            self.save()
            return True, "Sponsorship removed"
        return False, f"Not sponsoring {team_id}"

    def get_team_sponsors(self, team_id: str) -> List[ForemanProfile]:
        team = self._teams.get(team_id.upper())
        if not team:
            return []
        return [self._foremans[s] for s in team.sponsors
                if s in self._foremans]

    # ══════════════════════════════════════════════════════
    # PROJECT OWNERSHIP + CROSS-TEAM VALIDATION
    # ══════════════════════════════════════════════════════

    def assign_project(self, team_id: str, project_id: str) -> bool:
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        pid = project_id.upper()
        for other in self._teams.values():
            if other.team_id != team.team_id and pid in other.projects:
                print(f"[GOVERNANCE] BLOCKED: {pid} owned by {other.team_id}")
                return False
        if pid not in team.projects:
            team.projects.append(pid)
            self.save()
        return True

    def release_project(self, team_id: str, project_id: str) -> bool:
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        pid = project_id.upper()
        if pid in team.projects:
            team.projects.remove(pid)
            self.save()
            return True
        return False

    def get_project_owner(self, project_id: str) -> Optional[RDTeam]:
        pid = project_id.upper()
        for team in self._teams.values():
            if pid in team.projects:
                return team
        return None

    def is_member_of_project(self, person_name: str,
                             project_id: str) -> bool:
        owner = self.get_project_owner(project_id)
        if not owner:
            return True
        return any(m.name.lower() == person_name.lower()
                   for m in owner.members)

    def validate_inclusion_accept(self, observer_name: str,
                                  project_id: str) -> Tuple[bool, str]:
        owner = self.get_project_owner(project_id)
        if not owner:
            return True, "Project unregistered — open accept"
        if self.is_member_of_project(observer_name, project_id):
            return True, f"✓ {observer_name} is a member of {owner.team_id}"
        return False, (
            f"✗ BLOCKED: {observer_name} is not a member of "
            f"{owner.team_id} (owns {project_id}). "
            f"Cross-team injection prevented.")

    def validate_foreman_access(self, foreman_id: str,
                                   team_id: str) -> bool:
        """Can this foreman view this team? Only if sponsoring."""
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        return foreman_id in team.sponsors

    # ══════════════════════════════════════════════════════
    # TRIAD NOTE PROPAGATION
    # ══════════════════════════════════════════════════════

    def post_triad_note(self, foreman_id: str, team_id: str,
                        content: str, category: str = "GENERAL",
                        is_pinned: bool = False) -> Optional[TriadNote]:
        if not self.validate_foreman_access(foreman_id, team_id):
            print(f"[GOVERNANCE] Note BLOCKED: {foreman_id} "
                  f"not sponsoring {team_id}")
            return None

        foreman = self._foremans.get(foreman_id)
        if not foreman:
            return None

        ts = datetime.now().strftime("%Y%m%d")
        count = sum(1 for n in self._triad_notes
                    if n.note_id.startswith(f"TN-{ts}")) + 1
        note_id = f"TN-{ts}-{count:03d}"

        note = TriadNote(
            note_id=note_id, foreman_id=foreman_id,
            foreman_name=foreman.name,
            team_id=team_id.upper(), content=content,
            timestamp=datetime.now().isoformat(),
            category=category.upper(), master_lens=ML_FOREMAN,
            is_pinned=is_pinned,
        )
        self._triad_notes.append(note)
        self.save()
        print(f"[GOVERNANCE] Note {note_id}: {foreman.name} → {team_id}")
        return note

    def get_triad_notes(self, team_id: str,
                        limit: int = 50) -> List[TriadNote]:
        tid = team_id.upper()
        notes = [n for n in self._triad_notes if n.team_id == tid]
        pinned = sorted([n for n in notes if n.is_pinned],
                        key=lambda n: n.timestamp, reverse=True)
        regular = sorted([n for n in notes if not n.is_pinned],
                         key=lambda n: n.timestamp, reverse=True)
        return (pinned + regular)[:limit]

    def acknowledge_note(self, note_id: str, platform: str) -> bool:
        for note in self._triad_notes:
            if note.note_id == note_id:
                if platform not in note.acknowledged_by:
                    note.acknowledged_by.append(platform)
                    self.save()
                return True
        return False

    # ══════════════════════════════════════════════════════
    # FOOTPRINT TRACKING
    # ══════════════════════════════════════════════════════

    def log_footprint(self, user_name: str, user_type: str,
                      team_id: str, platform: str,
                      location: str, session_id: str = ""):
        """
        Record navigation event. Lightweight — buffered in memory.
        Call flush_footprints() on shutdown or periodically.
        """
        fp = Footprint(
            user_name=user_name, user_type=user_type,
            team_id=team_id.upper(), platform=platform,
            location=location, timestamp=datetime.now().isoformat(),
            session_id=session_id,
        )
        self._footprints.append(fp)

    def flush_footprints(self):
        """Write footprints to disk."""
        if self._footprints:
            self._save_footprints()
            print(f"[GOVERNANCE] Flushed {len(self._footprints)} footprints")

    def get_footprints(self, team_id: str = "", user_name: str = "",
                       platform: str = "",
                       limit: int = 200) -> List[Footprint]:
        results = self._footprints
        if team_id:
            tid = team_id.upper()
            results = [fp for fp in results if fp.team_id == tid]
        if user_name:
            results = [fp for fp in results
                       if fp.user_name.lower() == user_name.lower()]
        if platform:
            results = [fp for fp in results if fp.platform == platform]
        return results[-limit:]

    def get_engagement_metrics(self, team_id: str) -> Dict:
        """
        Derive engagement from footprints.
        Eager eyes tend to want to see — activity predicts success.
        """
        tid = team_id.upper()
        fps = [fp for fp in self._footprints if fp.team_id == tid]
        if not fps:
            return {"total_visits": 0, "unique_users": 0,
                    "platforms_touched": 0, "engagement_score": 0}

        unique_users = len(set(fp.user_name for fp in fps))
        platforms = len(set(fp.platform for fp in fps))
        unique_locs = len(set(fp.location for fp in fps))
        sessions = set()
        for fp in fps:
            sessions.add(fp.session_id if fp.session_id else fp.timestamp[:10])

        total = len(fps)
        breadth = platforms / 3.0
        try:
            last = max(fp.timestamp for fp in fps)
            days_ago = (datetime.now() - datetime.fromisoformat(last)).days
            recency = max(0, 1.0 - days_ago / 30.0)
        except Exception:
            recency = 0.5

        score = round(min(100, total * breadth * recency * 2), 1)

        return {
            "total_visits": total,
            "unique_users": unique_users,
            "unique_locations": unique_locs,
            "platforms_touched": platforms,
            "sessions": len(sessions),
            "engagement_score": score,
        }

    # ══════════════════════════════════════════════════════
    # ADMIN — Developer toggle
    # ══════════════════════════════════════════════════════

    def is_admin(self, person_name: str, team_id: str) -> bool:
        """Check if this person has admin flag on their team."""
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        for m in team.members:
            if m.name.lower() == person_name.lower():
                return m.is_admin
        return False

    def set_admin(self, person_name: str, team_id: str,
                  admin: bool = True) -> bool:
        """Set or clear admin flag for a team member."""
        team = self._teams.get(team_id.upper())
        if not team:
            return False
        for m in team.members:
            if m.name.lower() == person_name.lower():
                m.is_admin = admin
                self.save()
                print(f"[GOVERNANCE] {person_name} admin={'ON' if admin else 'OFF'} "
                      f"on {team_id}")
                return True
        print(f"[GOVERNANCE] {person_name} not found on {team_id}")
        return False

    def get_admin_members(self) -> List[Tuple[str, str]]:
        """List all admins across all teams. Returns [(name, team_id)]."""
        admins = []
        for team in self._teams.values():
            for m in team.members:
                if m.is_admin:
                    admins.append((m.name, team.team_id))
        return admins

    # ══════════════════════════════════════════════════════
    # CONVENIENCE
    # ══════════════════════════════════════════════════════

    def get_team_for_project(self, project_id: str) -> Optional[str]:
        owner = self.get_project_owner(project_id)
        return owner.team_id if owner else None

    def get_all_projects(self) -> Dict[str, str]:
        result = {}
        for team in self._teams.values():
            for pid in team.projects:
                result[pid] = team.team_id
        return result

    def summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════╗",
            "║       TEAM GOVERNANCE v2.0 — REGISTRY STATUS        ║",
            "╚══════════════════════════════════════════════════════╝", "",
        ]
        lines.append(f"Institutions: {len(self._institutions)}")
        for inst in self.list_institutions():
            ic = len(self.list_foremans(institution_id=inst.institution_id))
            lines.append(f"  {inst.institution_id}: {inst.name} "
                         f"[{inst.hub_region}] ({ic} foremans)")

        lines.append(f"\nForemans: {len(self._foremans)}")
        for i in self.list_foremans():
            teams = self.get_foreman_teams(i.foreman_id)
            tids = ", ".join(t.team_id for t in teams) or "(none)"
            lines.append(f"  {i.foreman_id}: {i.name} "
                         f"({i.institution_id}) → {tids}")

        lines.append(f"\nTeams: {len(self._teams)}")
        for t in self.list_teams():
            projs = ", ".join(t.projects) or "(none)"
            status = "SPONSORED" if t.is_sponsored else "UNSPONSORED"
            names = ", ".join(
                self._foremans[s].name for s in t.sponsors
                if s in self._foremans) or "—"
            lines.append(f"  {t.team_id}: {t.team_name} [{status}]")
            lines.append(f"    Projects: {projs}")
            lines.append(f"    Sponsors ({t.sponsor_count}/"
                         f"{MAX_SPONSORS_PER_TEAM}): {names}")

        lines.append(f"\nTriad Notes: {len(self._triad_notes)}")
        lines.append(f"Footprints: {len(self._footprints)}")
        return "\n".join(lines)


# ============================================================================
# SINGLETON
# ============================================================================

_REGISTRY: Optional[GovernanceRegistry] = None


def get_registry(filepath: Optional[Path] = None) -> GovernanceRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = GovernanceRegistry(filepath)
    return _REGISTRY


# ============================================================================
# BOOTSTRAP
# ============================================================================

def bootstrap_gibush(registry: Optional[GovernanceRegistry] = None):
    """Seed first institution + team. Idempotent."""
    reg = registry or get_registry()
    if reg.get_team("GIBUSH"):
        print("[GOVERNANCE] GIBUSH exists — skip")
        return

    reg.register_institution(
        institution_id="UMAINE", name="University of Maine",
        hub_region="New England",
    )

    reg.register_team(
        team_id="GIBUSH",
        team_name="Team GIBUSH — THE PIPE TALKERS",
        pin="000000",
        members=[{"name": "Stephen Burdick", "role": "EL",
                  "is_lead": True, "is_admin": True}],
        projects=["AISOS_SPINE", "BCM_SUBSTRATE"],
        institution="UMaine / MIT",
        program_type="Validation", hub_region="New England",
        test_batch_id="NE-FUS-2026S",
    )

    print("[GOVERNANCE] ✓ Bootstrap done — GIBUSH is UNSPONSORED")
    print("[GOVERNANCE] Foreman must register under UMAINE, then sponsor")
    print(reg.summary())


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    reg = get_registry()

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "bootstrap":
            bootstrap_gibush(reg)
        elif cmd == "summary":
            print(reg.summary())
        elif cmd == "verify-pin" and len(sys.argv) >= 4:
            ok = reg.authenticate_team(sys.argv[2], sys.argv[3])
            print(f"{'✓ OK' if ok else '✗ FAILED'}")
        elif cmd == "validate" and len(sys.argv) >= 4:
            ok, reason = reg.validate_inclusion_accept(sys.argv[2], sys.argv[3])
            print(reason)
        elif cmd == "list-teams":
            for t in reg.list_teams():
                s = "SPONSORED" if t.is_sponsored else "UNSPONSORED"
                print(f"  {t.team_id}: {t.team_name} [{s}]")
        elif cmd == "list-foremans":
            for i in reg.list_foremans():
                print(f"  {i.foreman_id}: {i.name} ({i.institution_id})")
        elif cmd == "list-institutions":
            for i in reg.list_institutions():
                print(f"  {i.institution_id}: {i.name} [{i.hub_region}]")
        elif cmd == "engagement" and len(sys.argv) >= 3:
            for k, v in reg.get_engagement_metrics(sys.argv[2]).items():
                print(f"  {k}: {v}")

        elif cmd == "set-admin" and len(sys.argv) >= 4:
            name = sys.argv[2]
            tid = sys.argv[3]
            reg.set_admin(name, tid, admin=True)

        elif cmd == "remove-admin" and len(sys.argv) >= 4:
            name = sys.argv[2]
            tid = sys.argv[3]
            reg.set_admin(name, tid, admin=False)

        elif cmd == "who-admin":
            admins = reg.get_admin_members()
            if admins:
                for name, tid in admins:
                    print(f"  {name} on {tid}")
            else:
                print("  No admins set")

        elif cmd == "reset":
            # Delete JSON and re-bootstrap
            if reg._filepath.exists():
                reg._filepath.unlink()
                print(f"[GOVERNANCE] Deleted {reg._filepath}")
            fp_file = reg._filepath.parent / "footprints.json"
            if fp_file.exists():
                fp_file.unlink()
                print(f"[GOVERNANCE] Deleted {fp_file}")
            # Clear in-memory state and re-bootstrap
            reg._institutions.clear()
            reg._foremans.clear()
            reg._teams.clear()
            reg._triad_notes.clear()
            reg._footprints.clear()
            bootstrap_gibush(reg)

        else:
            print("Commands: bootstrap, summary, reset, verify-pin, validate,")
            print("          list-teams, list-foremans, list-institutions,")
            print("          set-admin, remove-admin, who-admin, engagement")
    else:
        print("TEAM GOVERNANCE v2.0")
        print("Run: python team_governance.py bootstrap")
