// ============================================
// HELPERS GLOBAUX
// ============================================

/**
 * Helper pour préfixer automatiquement les URLs API avec root_path
 * Usage: apiUrl('/api/v1/users') => '/mppeep/api/v1/users' (en prod)
 */
window.apiUrl = window.apiUrl || function(path) {
    // Si le chemin commence déjà par root_path, le retourner tel quel
    if (window.root_path && path.startsWith(window.root_path)) {
        return path;
    }
    // Sinon, ajouter le préfixe
    return window.root_path ? window.root_path + path : path;
};

/**
 * Wrapper de fetch qui préfixe automatiquement les URLs API
 * Remplace le fetch natif pour gérer automatiquement le root_path
 */
(function() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options) {
        // Si l'URL est une chaîne et commence par /api/, /static/, ou /uploads/
        if (typeof url === 'string') {
            if (url.startsWith('/api/') || url.startsWith('/static/') || url.startsWith('/uploads/')) {
                url = window.apiUrl(url);
            }
        }
        
        // Appeler le fetch original avec l'URL préfixée
        return originalFetch(url, options);
    };
})();

// ============================================
// FONCTIONS UTILITAIRES
// ============================================

/**
 * Convertit FormData en objet JSON propre
 * - Convertit les chaînes vides en null pour les champs ID
 * - Nettoie les espaces inutiles
 * - Prépare les données pour l'envoi JSON
 * 
 * @param {FormData} formData - Le FormData à convertir
 * @returns {Object} - Objet nettoyé prêt pour JSON.stringify()
 */
window.formDataToCleanObject = function(formData) {
    const data = {};
    
    for (const [key, value] of formData.entries()) {
        // Convertir les chaînes vides en null pour les champs numériques (ID)
        if (value === '' && (key.endsWith('_id') || key === 'id')) {
            data[key] = null;
        }
        // Convertir "null" string en null
        else if (value === 'null') {
            data[key] = null;
        }
        // Nettoyer les espaces pour les chaînes
        else if (typeof value === 'string') {
            data[key] = value.trim();
        }
        // Garder les autres valeurs telles quelles
        else {
            data[key] = value;
        }
    }
    
    return data;
};

/**
 * Vérifie si un FormData contient des fichiers
 * @param {FormData} formData - Le FormData à vérifier
 * @returns {boolean} - true si contient des fichiers
 */
window.formDataHasFiles = function(formData) {
    for (const [key, value] of formData.entries()) {
        if (value instanceof File && value.size > 0) {
            return true;
        }
    }
    return false;
};

/**
 * Nettoie un FormData en supprimant toutes les valeurs vides
 * Les champs vides ne seront pas envoyés (= null côté serveur pour champs optionnels)
 * 
 * @param {FormData} formData - Le FormData à nettoyer
 * @returns {FormData} - Nouveau FormData nettoyé
 */
window.cleanFormData = function(formData) {
    const cleaned = new FormData();
    
    for (const [key, value] of formData.entries()) {
        // Si c'est un fichier, toujours l'ajouter
        if (value instanceof File) {
            cleaned.append(key, value);
        }
        // Si la valeur est vide, ne pas l'ajouter (sera null ou ignoré côté serveur)
        else if (value === '' || value === 'null' || value === 'undefined') {
            // Ne rien ajouter = champ absent = null pour les optionnels
        }
        // Si la valeur est remplie, l'ajouter après nettoyage des espaces
        else {
            cleaned.append(key, typeof value === 'string' ? value.trim() : value);
        }
    }
    
    return cleaned;
};

/**
 * Helper intelligent pour envoyer des données de formulaire
 * Détecte automatiquement si le formulaire contient des fichiers :
 * - Si oui : envoie en multipart/form-data (garde FormData)
 * - Si non : envoie en JSON (convertit et nettoie)
 * 
 * @param {string} url - L'URL de destination
 * @param {FormData} formData - Le FormData du formulaire
 * @param {string} method - La méthode HTTP (POST, PUT, etc.)
 * @param {boolean} forceFormData - Forcer l'utilisation de FormData même sans fichiers
 * @returns {Promise} - La promesse du fetch
 */
window.submitFormAsJson = async function(url, formData, method = 'POST', forceFormData = false) {
    // Si le formulaire contient des fichiers ou forceFormData=true, envoyer en multipart/form-data
    if (forceFormData || window.formDataHasFiles(formData)) {
        // Nettoyer le FormData (supprimer les valeurs vides des champs ID)
        const cleanedFormData = window.cleanFormData(formData);
        return fetch(url, {
            method: method,
            body: cleanedFormData  // Pas de Content-Type, le navigateur le gère automatiquement
        });
    }
    
    // Sinon, convertir en JSON et nettoyer
    const data = window.formDataToCleanObject(formData);
    
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
};

/**
 * Afficher un message de succès/erreur
 */
window.showMessage = window.showMessage || function(message, type = 'success') {
    console.log(`[${type.toUpperCase()}]`, message);
    // Cette fonction peut être surchargée par les pages individuelles
};

/**
 * Afficher un overlay de chargement
 */
window.showLoading = window.showLoading || function(text = 'Chargement...', subtext = 'Veuillez patienter') {
    console.log(`[LOADING] ${text} - ${subtext}`);
    // Cette fonction peut être surchargée par les pages individuelles
};

/**
 * Masquer l'overlay de chargement
 */
window.hideLoading = window.hideLoading || function() {
    console.log('[LOADING] Hidden');
    // Cette fonction peut être surchargée par les pages individuelles
};
