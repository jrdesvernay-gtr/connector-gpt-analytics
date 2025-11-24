#!/usr/bin/env python3
"""
List all workspaces in the database.
Shows workspace ID, user email, and creation date.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.workspace import Workspace
from app.models.user import User

def list_workspaces():
    """List all workspaces with their IDs and associated user info."""
    db: Session = SessionLocal()
    try:
        workspaces = (
            db.query(Workspace)
            .join(User, Workspace.user_id == User.id)
            .order_by(Workspace.created_at.desc())
            .all()
        )
        
        if not workspaces:
            print("No workspaces found in the database.")
            return
        
        print(f"\n{'='*80}")
        print(f"Found {len(workspaces)} workspace(s):")
        print(f"{'='*80}\n")
        
        for i, workspace in enumerate(workspaces, 1):
            user = db.query(User).filter(User.id == workspace.user_id).first()
            print(f"{i}. Workspace ID: {workspace.id}")
            print(f"   User Email: {user.email if user else 'Unknown'}")
            print(f"   Created At: {workspace.created_at}")
            print(f"   User ID: {workspace.user_id}")
            print()
        
        print(f"{'='*80}\n")
        print("Quick copy workspace IDs:")
        for workspace in workspaces:
            print(f"  {workspace.id}")
        print()
        
    except Exception as e:
        print(f"Error listing workspaces: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    list_workspaces()

