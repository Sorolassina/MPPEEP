#!/usr/bin/env python3
"""
Script pour vérifier les sessions via SQL direct
"""
import psycopg2
from datetime import datetime

# Configuration de connexion
DB_CONFIG = {
    'dbname': 'mppeep',
    'user': 'mppeepuser',
    'password': 'mppeep',
    'host': 'localhost',
    'port': '5432'
}

def main():
    print("\n" + "="*70)
    print("🔍 VÉRIFICATION DES SESSIONS UTILISATEUR (PostgreSQL)")
    print("="*70 + "\n")
    
    try:
        # Connexion à PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Compter les sessions
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_active = true) as actives,
                COUNT(*) FILTER (WHERE is_active = false) as inactives
            FROM user_sessions
        """)
        stats = cursor.fetchone()
        total, actives, inactives = stats
        
        print(f"📊 STATISTIQUES :")
        print(f"   Total sessions    : {total}")
        print(f"   ✅ Actives        : {actives}")
        print(f"   ❌ Inactives      : {inactives}")
        print()
        
        if total == 0:
            print("ℹ️  Aucune session trouvée dans la base de données.\n")
            conn.close()
            return
        
        # Récupérer les sessions actives
        if actives > 0:
            cursor.execute("""
                SELECT 
                    us.session_token,
                    us.user_id,
                    u.email,
                    us.device_info,
                    us.ip_address,
                    us.created_at,
                    us.last_activity,
                    us.expires_at,
                    us.is_active
                FROM user_sessions us
                LEFT JOIN "user" u ON us.user_id = u.id
                WHERE us.is_active = true
                ORDER BY us.last_activity DESC
            """)
            
            active_sessions = cursor.fetchall()
            
            print("🟢 SESSIONS ACTIVES (CONNECTÉES) :")
            print("-" * 70)
            
            for session in active_sessions:
                token, user_id, email, device, ip, created, last_act, expires, is_active = session
                
                # Calculer si expirée
                now = datetime.now()
                if expires.tzinfo:
                    from datetime import timezone
                    now = datetime.now(timezone.utc)
                
                is_expired = now > expires
                
                if expires > now:
                    remaining = expires - now
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    time_left = f"{days}j {hours}h"
                else:
                    time_left = "⚠️ EXPIRÉE"
                
                print(f"  👤 Utilisateur       : {email or f'User ID {user_id}'}")
                print(f"  🔑 Token             : {token[:25]}...")
                print(f"  💻 Appareil          : {device or 'Unknown'}")
                print(f"  🌐 IP                : {ip or 'Unknown'}")
                print(f"  📅 Créée le          : {created.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  🕐 Dernière activité : {last_act.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  ⏰ Expire le         : {expires.strftime('%Y-%m-%d %H:%M:%S')} ({time_left})")
                print(f"  {'⚠️  STATUS' if is_expired else '✅ STATUS'}            : {'🔴 EXPIRÉE' if is_expired else '🟢 VALIDE'}")
                print()
        else:
            print("✅ Aucune session active")
            print("   → Tous les utilisateurs sont déconnectés\n")
        
        # Récupérer les dernières sessions inactives
        if inactives > 0:
            cursor.execute("""
                SELECT 
                    us.session_token,
                    u.email,
                    us.device_info,
                    us.last_activity
                FROM user_sessions us
                LEFT JOIN "user" u ON us.user_id = u.id
                WHERE us.is_active = false
                ORDER BY us.last_activity DESC
                LIMIT 5
            """)
            
            inactive_sessions = cursor.fetchall()
            
            print("🔴 SESSIONS INACTIVES (DÉCONNECTÉES) - 5 plus récentes :")
            print("-" * 70)
            
            for session in inactive_sessions:
                token, email, device, last_act = session
                print(f"  👤 Utilisateur       : {email or 'Unknown'}")
                print(f"  🔑 Token             : {token[:25]}...")
                print(f"  💻 Appareil          : {device or 'Unknown'}")
                print(f"  🕐 Dernière activité : {last_act.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  🚪 Déconnexion       : Session désactivée (is_active=false)")
                print()
            
            if inactives > 5:
                print(f"  ... et {inactives - 5} session(s) inactives supplémentaires\n")
        
        print("="*70)
        print()
        
        # Résumé final
        if actives > 0:
            print("⚠️  ATTENTION : Vous avez", actives, "session(s) active(s) !")
            print("   → Si vous venez de cliquer sur Déconnexion,")
            print("   → cela signifie que la session N'A PAS ÉTÉ désactivée (BUG!).")
            print()
            print("💡 VÉRIFICATION : Essayez d'accéder à une page protégée")
            print("   → Si vous êtes redirigé vers login : le cookie est supprimé (OK)")
            print("   → Si vous accédez à la page : BUG de déconnexion!")
        else:
            print("✅ PARFAIT : Aucune session active !")
            print("   → La déconnexion a bien fonctionné.")
            print("   → Toutes les sessions ont été désactivées (is_active=false).")
        
        print()
        
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Erreur de connexion à PostgreSQL:")
        print(f"   {e}")
        print()
        print("💡 Vérifiez que PostgreSQL est démarré et accessible.")
        print()
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

