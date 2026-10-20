<?php
/**
 * License Validation API
 * Επικυρώνει license keys με API key authentication
 * 
 * Usage: https://pcp.com.gr/validate_license.php?key=DEMO-1YEAR
 * Header: X-API-KEY: your-secret-api-key-here
 */

// Ρυθμίσεις
define('API_KEY', 'CHANGE_ME_API_KEY');  // API Key - Keep Secret!
define('LICENSES_DIR', __DIR__ . '/licenses');  // Φάκελος με τα JSON files

// CORS Headers (προαιρετικό - αν χρειάζεται)
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: X-API-KEY, Content-Type');

// Handle OPTIONS request (preflight)
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Έλεγχος API Key
$provided_key = '';

// Έλεγχος σε header
if (isset($_SERVER['HTTP_X_API_KEY'])) {
    $provided_key = $_SERVER['HTTP_X_API_KEY'];
}
// Fallback: Έλεγχος σε GET parameter (λιγότερο ασφαλές)
elseif (isset($_GET['api_key'])) {
    $provided_key = $_GET['api_key'];
}

if ($provided_key !== API_KEY) {
    http_response_code(403);
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Unauthorized',
        'message' => 'Invalid API key'
    ]);
    exit;
}

// Λήψη license key από URL
$license_key = isset($_GET['key']) ? $_GET['key'] : '';

if (empty($license_key)) {
    http_response_code(400);
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Bad Request',
        'message' => 'License key is required'
    ]);
    exit;
}

// Καθαρισμός license key (ασφάλεια)
$license_key = preg_replace('/[^A-Z0-9\-]/', '', strtoupper($license_key));

// Εύρεση JSON file
$json_file = LICENSES_DIR . '/' . $license_key . '.json';

if (!file_exists($json_file)) {
    http_response_code(404);
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Not Found',
        'message' => 'License key not found'
    ]);
    exit;
}

// Διάβασμα και επιστροφή JSON
$json_content = file_get_contents($json_file);
$license_data = json_decode($json_content, true);

if ($license_data === null) {
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Internal Server Error',
        'message' => 'Invalid JSON format'
    ]);
    exit;
}

// Επιτυχής απάντηση
http_response_code(200);
header('Content-Type: application/json');
echo json_encode($license_data);
?>
