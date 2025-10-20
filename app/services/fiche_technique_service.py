# app/services/fiche_technique_service.py
"""
Service de traitement des fiches techniques budgétaires
Gère l'import, la validation et la création de fiches depuis des fichiers Excel
"""

from decimal import Decimal
from io import BytesIO

import pandas as pd
from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.core.logging_config import get_logger
from app.models.budget import (
    ActionBudgetaire,
    ActiviteBudgetaire,
    FicheTechnique,
    LigneBudgetaireDetail,
    ServiceBeneficiaire,
)
from app.models.personnel import Programme
from app.models.user import User

logger = get_logger(__name__)


class FicheTechniqueService:
    """Service pour gérer les fiches techniques budgétaires"""

    @staticmethod
    def analyser_fichier_excel(
        content: bytes, nom_fiche: str | None, programme_id: int, annee: int, session: Session, current_user: User
    ) -> dict:
        """
        Analyser un fichier Excel de fiche technique avec le template standardisé

        Args:
            content: Contenu binaire du fichier Excel
            nom_fiche: Nom optionnel de la fiche
            programme_id: ID du programme budgétaire
            annee: Année budgétaire (N+1)
            session: Session de base de données
            current_user: Utilisateur qui effectue l'import

        Returns:
            dict avec résumé de l'import (compteurs, budget total, erreurs)

        Raises:
            HTTPException si le fichier n'est pas conforme au template
        """
        try:
            # Lire le fichier Excel (ligne 1 = en-têtes)
            df = pd.read_excel(BytesIO(content))

            logger.info(f"📊 Lecture fichier : {len(df)} lignes, {len(df.columns)} colonnes")
            logger.info(f"📋 Colonnes : {df.columns.tolist()}")

            # Valider et mapper les colonnes
            colonnes_mappees = FicheTechniqueService._valider_et_mapper_colonnes(df)

            # Créer la fiche technique avec l'année spécifiée
            fiche = FicheTechniqueService._creer_fiche_technique(
                df, colonnes_mappees, nom_fiche, programme_id, annee, session, current_user
            )

            # Créer la structure hiérarchique
            result = FicheTechniqueService._creer_structure_hierarchique(df, colonnes_mappees, fiche.id, session)

            logger.info(f"✅ Fiche technique chargée : {fiche.numero_fiche}")

            return {
                "ok": True,
                "fiche_numero": fiche.numero_fiche,
                "actions_count": result["actions_count"],
                "services_count": result["services_count"],
                "activites_count": result["activites_count"],
                "lignes_count": result["lignes_count"],
                "budget_total": float(result["budget_total"]),
                "errors": result["errors"],
            }

        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Erreur analyse Excel: {e}")
            raise HTTPException(500, f"Erreur analyse Excel: {e!s}")

    @staticmethod
    def _valider_et_mapper_colonnes(df: pd.DataFrame) -> dict[str, str]:
        """
        Valide que le fichier correspond au template et mappe les colonnes

        Returns:
            dict: Mapping des colonnes {'code_libelle': 'CODE / LIBELLE', ...}

        Raises:
            HTTPException si colonnes essentielles manquantes
        """
        logger.info("🔍 Validation du template fiche technique...")

        # Nettoyer les noms de colonnes
        df.columns = [str(col).replace("\n", " ").strip() for col in df.columns]

        # Mapping des colonnes
        colonnes_mappees = {}

        # Patterns de détection (flexibles pour N/N+1 OU années réelles)
        patterns_colonnes = {
            "code_libelle": [("CODE", "LIBELLE")],
            "budget_vote_n": [("BUDGET", "VOTE"), ("BUDGET", "VOTÉ")],
            "budget_actuel_n": [("BUDGET", "ACTUEL")],
            "enveloppe_n_plus_1": [("ENVELOPPE",)],
            "complement_solicite": [("COMPLEMENT", "SOLLICITÉ"), ("COMPLEMENT", "SOLLICITE")],
            "budget_souhaite": [("BUDGET", "SOUHAITÉ"), ("BUDGET", "SOUHAITE")],
            "engagement_etat": [("ENGAGEMENT", "ÉTAT"), ("ENGAGEMENT", "ETAT")],
            "autre_complement": [("AUTRE", "COMPLEMENT")],
            "projet_budget_n_plus_1": [("PROJET", "BUDGET")],
            "justificatifs": [("JUSTIFICATIF",)],
        }

        # Détecter chaque colonne
        for nom_standard, liste_patterns in patterns_colonnes.items():
            for col in df.columns:
                col_upper = str(col).upper().replace("É", "E").replace("È", "E").replace("Ê", "E")

                for patterns in liste_patterns:
                    if all(p in col_upper for p in patterns):
                        colonnes_mappees[nom_standard] = col
                        logger.debug(f"  ✓ {nom_standard} → {col}")
                        break

                if nom_standard in colonnes_mappees:
                    break

        # Validation des colonnes essentielles
        colonnes_essentielles = ["code_libelle", "budget_vote_n", "enveloppe_n_plus_1"]
        colonnes_manquantes = [c for c in colonnes_essentielles if c not in colonnes_mappees]

        if colonnes_manquantes:
            logger.error(f"❌ Colonnes essentielles manquantes : {colonnes_manquantes}")
            raise HTTPException(
                400,
                f"❌ Le fichier ne correspond pas au template de fiche technique.\n\n"
                f"Colonnes manquantes : {', '.join(colonnes_manquantes)}\n\n"
                f"💡 Téléchargez le modèle Excel pour obtenir la structure correcte.",
            )

        logger.info(f"✅ Template validé : {len(colonnes_mappees)}/10 colonnes détectées")

        return colonnes_mappees

    @staticmethod
    def _creer_fiche_technique(
        df: pd.DataFrame,
        colonnes_mappees: dict,
        nom_fiche: str | None,
        programme_id: int,
        annee: int,
        session: Session,
        current_user: User,
    ) -> FicheTechnique:
        """Créer une fiche technique depuis le template"""
        logger.info(f"📅 Année de la fiche : {annee}")

        # Générer numéro de fiche
        count = session.exec(select(func.count(FicheTechnique.id)).where(FicheTechnique.annee_budget == annee)).one()

        prog = session.get(Programme, programme_id)
        if not prog:
            raise HTTPException(400, "Programme non trouvé")

        numero_fiche = nom_fiche or f"FT-{annee}-{prog.code}-{count + 1:03d}"

        fiche = FicheTechnique(
            numero_fiche=numero_fiche,
            annee_budget=annee,
            programme_id=programme_id,
            direction_id=None,
            budget_total_demande=Decimal("0"),
            statut="Brouillon",
            phase="Conférence interne",
            created_by_user_id=current_user.id,
        )

        session.add(fiche)
        session.commit()
        session.refresh(fiche)

        logger.info(f"✅ Fiche créée : {fiche.numero_fiche}")

        return fiche

    @staticmethod
    def _creer_structure_hierarchique(
        df: pd.DataFrame, colonnes_mappees: dict, fiche_id: int, session: Session
    ) -> dict:
        """Créer la hiérarchie complète depuis le template"""
        actions_count = 0
        services_count = 0
        activites_count = 0
        lignes_count = 0
        budget_total = Decimal("0")
        errors = []

        current_nature = None
        current_action = None
        current_service = None
        current_activite = None

        col_code_libelle = colonnes_mappees.get("code_libelle")

        logger.info(f"📊 Import de {len(df)} lignes...")

        for idx, row in df.iterrows():
            try:
                code_libelle = str(row[col_code_libelle]).strip()

                if not code_libelle or code_libelle == "nan":
                    continue

                # Nature de dépenses
                if code_libelle.upper() in [
                    "BIENS ET SERVICES",
                    "PERSONNEL",
                    "INVESTISSEMENT",
                    "INVESTISSEMENTS",
                    "TRANSFERTS",
                ]:
                    current_nature = code_libelle
                    current_action = None
                    current_service = None
                    current_activite = None
                    logger.info(f"📌 Nature : {current_nature}")
                    continue

                # Action
                if code_libelle.strip().startswith("Action :") or code_libelle.strip().startswith("- Action :"):
                    current_action = FicheTechniqueService._creer_action(
                        row, colonnes_mappees, fiche_id, current_nature, session
                    )
                    actions_count += 1
                    current_service = None
                    current_activite = None
                    logger.debug(f"  → ACTION : {code_libelle[:60]}")
                    continue

                # Service
                if code_libelle.strip().startswith("Service Bénéficiaire :") or code_libelle.strip().startswith(
                    "- Service Bénéficiaire :"
                ):
                    if current_action:
                        current_service = FicheTechniqueService._creer_service(
                            row, colonnes_mappees, fiche_id, current_action.id, session
                        )
                        services_count += 1
                        current_activite = None
                        logger.debug(f"    → SERVICE : {code_libelle[:60]}")
                    else:
                        errors.append(f"Ligne {idx + 2}: Service sans action")
                    continue

                # Activité
                if code_libelle.strip().startswith("Activité :") or code_libelle.strip().startswith("- Activité :"):
                    if current_service:
                        current_activite = FicheTechniqueService._creer_activite(
                            row, colonnes_mappees, fiche_id, current_service.id, session
                        )
                        activites_count += 1
                        logger.debug(f"      → ACTIVITÉ : {code_libelle[:60]}")
                    else:
                        errors.append(f"Ligne {idx + 2}: Activité sans service")
                    continue

                # Ligne budgétaire
                if current_activite:
                    ligne = FicheTechniqueService._creer_ligne(
                        row, colonnes_mappees, fiche_id, current_activite.id, session
                    )
                    lignes_count += 1
                    budget_total += ligne.budget_souhaite or Decimal("0")
                    logger.debug(f"        → LIGNE : {code_libelle[:60]}")
                else:
                    errors.append(f"Ligne {idx + 2}: Ligne sans activité")

            except Exception as e:
                errors.append(f"Ligne {idx + 2}: {e!s}")
                logger.error(f"❌ Erreur ligne {idx + 2}: {e}")

        logger.info(
            f"📊 Résumé : {actions_count} actions, {services_count} services, {activites_count} activités, {lignes_count} lignes"
        )

        # Recalculer totaux
        FicheTechniqueService._recalculer_totaux_hierarchie(fiche_id, session)

        # Mettre à jour budget total de la fiche
        fiche = session.get(FicheTechnique, fiche_id)
        if fiche:
            fiche.budget_total_demande = budget_total
            session.add(fiche)
            session.commit()

        logger.info(f"✅ Import terminé : Budget total = {budget_total:,.0f} FCFA")

        return {
            "actions_count": actions_count,
            "services_count": services_count,
            "activites_count": activites_count,
            "lignes_count": lignes_count,
            "budget_total": budget_total,
            "errors": errors,
        }

    @staticmethod
    def _get_decimal_from_row(row, colonnes_mappees: dict, col_name: str) -> Decimal:
        """Extraire une valeur décimale d'une ligne Excel de manière sécurisée"""
        if col_name in colonnes_mappees:
            val = row[colonnes_mappees[col_name]]
            if pd.notna(val) and str(val).strip() != "":
                try:
                    return Decimal(str(val).replace(" ", "").replace(",", ""))
                except:
                    return Decimal("0")
        return Decimal("0")

    @staticmethod
    def _creer_action(
        row, colonnes_mappees: dict, fiche_id: int, nature_depense: str | None, session: Session
    ) -> ActionBudgetaire:
        """Créer une action budgétaire depuis une ligne du template"""
        col_code_libelle = colonnes_mappees["code_libelle"]
        libelle_brut = str(row[col_code_libelle]).strip()

        # Nettoyer le libellé
        libelle = libelle_brut.replace("Action :", "").replace("- Action :", "").strip()

        # Code auto-incrémenté
        code = f"ACT_{len(session.exec(select(ActionBudgetaire)).all()) + 1:03d}"

        get_dec = lambda col: FicheTechniqueService._get_decimal_from_row(row, colonnes_mappees, col)

        action = ActionBudgetaire(
            fiche_technique_id=fiche_id,
            nature_depense=nature_depense,
            code=code,
            libelle=libelle,
            budget_vote_n=get_dec("budget_vote_n"),
            budget_actuel_n=get_dec("budget_actuel_n"),
            enveloppe_n_plus_1=get_dec("enveloppe_n_plus_1"),
            complement_solicite=get_dec("complement_solicite"),
            budget_souhaite=get_dec("budget_souhaite"),
            engagement_etat=get_dec("engagement_etat"),
            autre_complement=get_dec("autre_complement"),
            projet_budget_n_plus_1=get_dec("projet_budget_n_plus_1"),
            justificatifs=str(row[colonnes_mappees["justificatifs"]])
            if "justificatifs" in colonnes_mappees and pd.notna(row[colonnes_mappees["justificatifs"]])
            else None,
        )

        session.add(action)
        session.commit()
        session.refresh(action)

        return action

    @staticmethod
    def _creer_service(
        row, colonnes_mappees: dict, fiche_id: int, action_id: int, session: Session
    ) -> ServiceBeneficiaire:
        """Créer un service bénéficiaire depuis une ligne du template"""
        col_code_libelle = colonnes_mappees["code_libelle"]
        libelle_brut = str(row[col_code_libelle]).strip()

        # Nettoyer le libellé
        libelle = libelle_brut.replace("Service Bénéficiaire :", "").replace("- Service Bénéficiaire :", "").strip()

        # Code auto-incrémenté
        code = f"SRV_{len(session.exec(select(ServiceBeneficiaire)).all()) + 1:03d}"

        service = ServiceBeneficiaire(fiche_technique_id=fiche_id, action_id=action_id, code=code, libelle=libelle)

        session.add(service)
        session.commit()
        session.refresh(service)

        return service

    @staticmethod
    def _creer_activite(
        row, colonnes_mappees: dict, fiche_id: int, service_id: int, session: Session
    ) -> ActiviteBudgetaire:
        """Créer une activité budgétaire depuis une ligne du template"""
        col_code_libelle = colonnes_mappees["code_libelle"]
        libelle_brut = str(row[col_code_libelle]).strip()

        # Nettoyer le libellé
        libelle = libelle_brut.replace("Activité :", "").replace("- Activité :", "").strip()

        # Code auto-incrémenté
        code = f"ACTIV_{len(session.exec(select(ActiviteBudgetaire)).all()) + 1:03d}"

        get_dec = lambda col: FicheTechniqueService._get_decimal_from_row(row, colonnes_mappees, col)

        activite = ActiviteBudgetaire(
            fiche_technique_id=fiche_id,
            service_beneficiaire_id=service_id,
            code=code,
            libelle=libelle,
            budget_vote_n=get_dec("budget_vote_n"),
            budget_actuel_n=get_dec("budget_actuel_n"),
            enveloppe_n_plus_1=get_dec("enveloppe_n_plus_1"),
            complement_solicite=get_dec("complement_solicite"),
            budget_souhaite=get_dec("budget_souhaite"),
            engagement_etat=get_dec("engagement_etat"),
            autre_complement=get_dec("autre_complement"),
            projet_budget_n_plus_1=get_dec("projet_budget_n_plus_1"),
            justificatifs=str(row[colonnes_mappees["justificatifs"]])
            if "justificatifs" in colonnes_mappees and pd.notna(row[colonnes_mappees["justificatifs"]])
            else None,
        )

        session.add(activite)
        session.commit()
        session.refresh(activite)

        return activite

    @staticmethod
    def _creer_ligne(
        row, colonnes_mappees: dict, fiche_id: int, activite_id: int, session: Session
    ) -> LigneBudgetaireDetail:
        """Créer une ligne budgétaire depuis une ligne du template"""
        col_code_libelle = colonnes_mappees["code_libelle"]
        libelle = str(row[col_code_libelle]).strip()

        # Code auto-incrémenté
        code = f"LIGNE_{len(session.exec(select(LigneBudgetaireDetail)).all()) + 1:05d}"

        get_dec = lambda col: FicheTechniqueService._get_decimal_from_row(row, colonnes_mappees, col)

        ligne = LigneBudgetaireDetail(
            fiche_technique_id=fiche_id,
            activite_id=activite_id,
            code=code,
            libelle=libelle,
            budget_vote_n=get_dec("budget_vote_n"),
            budget_actuel_n=get_dec("budget_actuel_n"),
            enveloppe_n_plus_1=get_dec("enveloppe_n_plus_1"),
            complement_solicite=get_dec("complement_solicite"),
            budget_souhaite=get_dec("budget_souhaite"),
            engagement_etat=get_dec("engagement_etat"),
            autre_complement=get_dec("autre_complement"),
            projet_budget_n_plus_1=get_dec("projet_budget_n_plus_1"),
            justificatifs=str(row[colonnes_mappees["justificatifs"]])
            if "justificatifs" in colonnes_mappees and pd.notna(row[colonnes_mappees["justificatifs"]])
            else None,
        )

        session.add(ligne)
        session.commit()
        session.refresh(ligne)

        return ligne

    @staticmethod
    def _recalculer_totaux_hierarchie(fiche_id: int, session: Session):
        """
        Recalcule tous les totaux de bas en haut
        Lignes → Activités → Services → Actions
        """
        # 1. Recalculer totaux des activités (somme des lignes)
        activites = session.exec(
            select(ActiviteBudgetaire).where(ActiviteBudgetaire.fiche_technique_id == fiche_id)
        ).all()

        for activite in activites:
            lignes = session.exec(
                select(LigneBudgetaireDetail).where(LigneBudgetaireDetail.activite_id == activite.id)
            ).all()

            if lignes:
                activite.budget_vote_n = sum(l.budget_vote_n or Decimal("0") for l in lignes)
                activite.budget_actuel_n = sum(l.budget_actuel_n or Decimal("0") for l in lignes)
                activite.enveloppe_n_plus_1 = sum(l.enveloppe_n_plus_1 or Decimal("0") for l in lignes)
                activite.complement_solicite = sum(l.complement_solicite or Decimal("0") for l in lignes)
                activite.budget_souhaite = sum(l.budget_souhaite or Decimal("0") for l in lignes)
                activite.engagement_etat = sum(l.engagement_etat or Decimal("0") for l in lignes)
                activite.autre_complement = sum(l.autre_complement or Decimal("0") for l in lignes)
                activite.projet_budget_n_plus_1 = sum(l.projet_budget_n_plus_1 or Decimal("0") for l in lignes)
                session.add(activite)

        session.commit()

        # 2. Recalculer totaux des actions (somme des activités via services)
        actions = session.exec(select(ActionBudgetaire).where(ActionBudgetaire.fiche_technique_id == fiche_id)).all()

        for action in actions:
            services = session.exec(select(ServiceBeneficiaire).where(ServiceBeneficiaire.action_id == action.id)).all()

            total_budget_vote = Decimal("0")
            total_budget_actuel = Decimal("0")
            total_enveloppe = Decimal("0")
            total_complement = Decimal("0")
            total_budget_souhaite = Decimal("0")
            total_engagement = Decimal("0")
            total_autre = Decimal("0")
            total_projet = Decimal("0")

            for service in services:
                activites_service = session.exec(
                    select(ActiviteBudgetaire).where(ActiviteBudgetaire.service_beneficiaire_id == service.id)
                ).all()

                for activite in activites_service:
                    total_budget_vote += activite.budget_vote_n or Decimal("0")
                    total_budget_actuel += activite.budget_actuel_n or Decimal("0")
                    total_enveloppe += activite.enveloppe_n_plus_1 or Decimal("0")
                    total_complement += activite.complement_solicite or Decimal("0")
                    total_budget_souhaite += activite.budget_souhaite or Decimal("0")
                    total_engagement += activite.engagement_etat or Decimal("0")
                    total_autre += activite.autre_complement or Decimal("0")
                    total_projet += activite.projet_budget_n_plus_1 or Decimal("0")

            action.budget_vote_n = total_budget_vote
            action.budget_actuel_n = total_budget_actuel
            action.enveloppe_n_plus_1 = total_enveloppe
            action.complement_solicite = total_complement
            action.budget_souhaite = total_budget_souhaite
            action.engagement_etat = total_engagement
            action.autre_complement = total_autre
            action.projet_budget_n_plus_1 = total_projet
            session.add(action)

        session.commit()

        logger.info(f"✅ Totaux hiérarchiques recalculés pour fiche {fiche_id}")
