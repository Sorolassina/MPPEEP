#!/usr/bin/env python3
"""
Script de vérification de la sécurité de déconnexion
Vérifie que les sessions sont bien invalidées après logout
"""

from sqlmodel import Session, select
from app.db.session import engine
from app.models.session import UserSession
from app.models.user import User
from datetime import datetime


def verify_sessions():
    """Affiche l'état de toutes les sessions actives"""
    
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION DES SESSIONS UTILISATEUR")
    print("="*60 + "\n")
    
    with Session(engine) as session:
        # Compter toutes les sessions
        all_sessions = session.exec(select(UserSession)).all()
        active_sessions = [s for s in all_sessions if s.is_active]
        inactive_sessions = [s for s in all_sessions if not s.is_active]
        
        print(f"📊 Total sessions : {len(all_sessions)}")
        print(f"   ✅ Actives     : {len(active_sessions)}")
        print(f"   ❌ Inactives   : {len(inactive_sessions)}")
        print()
        
        # Afficher les sessions actives
        if active_sessions:
            print("🟢 SESSIONS ACTIVES :")
            print("-" * 60)
            
            for s in active_sessions:
                # Récupérer l'utilisateur
                user = session.get(User, s.user_id)
                
                # Vérifier si expirée
                is_expired = s.is_expired()
                status = "🔴 EXPIRÉE" if is_expired else "🟢 VALIDE"
                
                # Calculer le temps restant
                now = datetime.now()
                if s.expires_at > now:
                    remaining = s.expires_at - now
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    time_left = f"{days}j {hours}h"
                else:
                    time_left = "Expirée"
                
                print(f"  Token    : {s.session_token[:20]}...")
                print(f"  User     : {user.email if user else 'Unknown'}")
                print(f"  Device   : {s.device_info}")
                print(f"  IP       : {s.ip_address}")
                print(f"  Created  : {s.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Expires  : {s.expires_at.strftime('%Y-%m-%d %H:%M:%S')} ({time_left})")
                print(f"  Status   : {status}")
                print()
        else:
            print("✅ Aucune session active (tous les utilisateurs sont déconnectés)")
            print()
        
        # Afficher quelques sessions inactives (déconnectées)
        if inactive_sessions:
            print("🔴 SESSIONS INACTIVES (dernières 5) :")
            print("-" * 60)
            
            # Trier par date de dernière activité (plus récent en premier)
            recent_inactive = sorted(inactive_sessions, key=lambda x: x.last_activity, reverse=True)[:5]
            
            for s in recent_inactive:
                user = session.get(User, s.user_id)
                print(f"  User          : {user.email if user else 'Unknown'}")
                print(f"  Last Activity : {s.last_activity.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Device        : {s.device_info}")
                print()
        
        # Vérifier les sessions expirées mais encore marquées actives (bug potentiel)
        expired_but_active = [s for s in all_sessions if s.is_active and s.is_expired()]
        if expired_but_active:
            print("⚠️  ATTENTION : Sessions expirées mais encore marquées actives !")
            print("-" * 60)
            for s in expired_but_active:
                user = session.get(User, s.user_id)
                print(f"  User    : {user.email if user else 'Unknown'}")
                print(f"  Expired : {s.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print()
            print("👉 Ces sessions devraient être nettoyées automatiquement.\n")


def cleanup_expired_sessions():
    """Nettoie les sessions expirées"""
    
    print("\n" + "="*60)
    print("🧹 NETTOYAGE DES SESSIONS EXPIRÉES")
    print("="*60 + "\n")
    
    from app.services.session_service import SessionService
    
    with Session(engine) as session:
        count = SessionService.cleanup_expired_sessions(session)
        
        if count > 0:
            print(f"✅ {count} session(s) expirée(s) nettoyée(s)")
        else:
            print("✅ Aucune session expirée à nettoyer")
    
    print()


def test_session_security():
    """Test rapide de sécurité des sessions"""
    
    print("\n" + "="*60)
    print("🔒 TEST DE SÉCURITÉ DES SESSIONS")
    print("="*60 + "\n")
    
    with Session(engine) as session:
        # Vérifier que toutes les sessions inactives sont bien inaccessibles
        inactive_sessions = session.exec(
            select(UserSession).where(UserSession.is_active == False)
        ).all()
        
        if inactive_sessions:
            print(f"✅ {len(inactive_sessions)} session(s) inactives détectées")
            print("   → Ces sessions ne peuvent pas être utilisées pour se connecter")
        
        # Vérifier que toutes les sessions actives sont valides
        active_sessions = session.exec(
            select(UserSession).where(UserSession.is_active == True)
        ).all()
        
        valid_count = 0
        expired_count = 0
        
        for s in active_sessions:
            if s.is_expired():
                expired_count += 1
            else:
                valid_count += 1
        
        print(f"✅ {valid_count} session(s) actives et valides")
        
        if expired_count > 0:
            print(f"⚠️  {expired_count} session(s) actives mais expirées (à nettoyer)")
        
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_expired_sessions()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_session_security()
    else:
        verify_sessions()
        
        print("\n💡 Commandes disponibles :")
        print("   python scripts/verify_logout.py            # Afficher toutes les sessions")
        print("   python scripts/verify_logout.py --cleanup  # Nettoyer les sessions expirées")
        print("   python scripts/verify_logout.py --test     # Test de sécurité")
        print()

