<?php
/**
 * Configuración administrativa de la demo (se ejecuta DENTRO del contenedor GLPI, como www-data):
 *  1. Habilita la API v2 (High-Level API) y la API heredada (solo para el enlace ticket<->equipo,
 *     que la v2.3 no expone en escritura).
 *  2. Crea el perfil "Integración GSPN (demo)" con permisos mínimos (clonado de Technician y recortado).
 *  3. Crea/actualiza el usuario de integración y le asigna el perfil en la entidad raíz (recursivo).
 *  4. Crea el cliente OAuth (grant password, scope api) para la API v2.
 *  5. Genera el token de API heredada del usuario de integración.
 * Idempotente: si ya existe cada objeto, lo reutiliza. Imprime UN JSON en stdout con los secretos
 * (el wrapper setup_integration.sh los guarda en .env sin mostrarlos).
 * Uso: php glpi_admin_setup.php <usuario> <password>
 */
declare(strict_types=1);

require '/var/www/glpi/vendor/autoload.php';
$kernel = new \Glpi\Kernel\Kernel();
$kernel->boot();
global $DB, $CFG_GLPI;

[$_, $login, $password, $tech_login] = $argv + [null, null, null, null];
if (!$login || !$password) { fwrite(STDERR, "uso: php glpi_admin_setup.php <usuario> <password>\n"); exit(2); }

// Contexto mínimo de sesión para que CommonDBTM::add() funcione en CLI (equivalente a un admin en consola).
$_SESSION['glpiID'] = 2; $_SESSION['glpiname'] = 'glpi';
$_SESSION['glpiactive_entity'] = 0; $_SESSION['glpiactiveentities'] = [0]; $_SESSION['glpiactiveentities_string'] = "'0'";
$_SESSION['glpishowallentities'] = 1; $_SESSION['glpiactiveprofile'] = ['id' => 4, 'name' => 'Super-Admin', 'interface' => 'central'];
$_SESSION['glpi_currenttime'] = date('Y-m-d H:i:s');

$out = ['steps' => []];

// 1. APIs
foreach (['enable_hlapi' => '1', 'enable_api' => '1', 'enable_api_login_external_token' => '1'] as $k => $v) {
    $DB->update('glpi_configs', ['value' => $v], ['name' => $k, 'context' => 'core']);
}
$out['steps'][] = 'apis_enabled';
// URL pública (detrás del proxy). Si GLPI_URL_BASE está definida en el entorno del contenedor, se fija url_base.
$url_base = trim((string) getenv('GLPI_URL_BASE'));
if ($url_base !== '') {
    $DB->update('glpi_configs', ['value' => rtrim($url_base, '/')], ['name' => 'url_base', 'context' => 'core']);
    $out['steps'][] = 'url_base_set';
}

// 2. Perfil con permisos mínimos
const PROFILE_NAME = 'Integración GSPN (demo)';
$profile = new Profile();
if (!$profile->getFromDBByCrit(['name' => PROFILE_NAME])) {
    $tech = new Profile(); $tech->getFromDB(6); // Technician como base de campos no-rights
    $pid = $profile->add([
        'name' => PROFILE_NAME, 'interface' => 'central', 'comment' => 'Perfil de la cuenta de integración de la demo GLPI<->Odoo. Permisos mínimos.',
        'helpdesk_hardware' => $tech->fields['helpdesk_hardware'], 'helpdesk_item_type' => importArrayFromDB($tech->fields['helpdesk_item_type']),
        'ticket_status' => importArrayFromDB($tech->fields['ticket_status']), 'problem_status' => importArrayFromDB($tech->fields['problem_status']),
        'change_status' => importArrayFromDB($tech->fields['change_status']), 'managed_domainrecordtypes' => [],
    ]);
    if (!$pid) { fwrite(STDERR, "no se pudo crear el perfil\n"); exit(1); }
    $profile->getFromDB($pid);
    $out['steps'][] = 'profile_created';
} else {
    $out['steps'][] = 'profile_exists';
}
$pid = (int) $profile->getID();
// Base: derechos del perfil Technician; luego se recortan y se añaden los estrictamente necesarios.
$rights = [];
foreach ($DB->request(['FROM' => 'glpi_profilerights', 'WHERE' => ['profiles_id' => 6]]) as $r) { $rights[$r['name']] = (int) $r['rights']; }
$zero = ['knowbase','project','projecttask','problem','change','changevalidation','reservation','planning','software','printer','monitor',
    'networking','peripheral','cartridge','consumable','license','certificate','line','domain','appliance','cluster','database','datacenter',
    'budget','contract','contact_enterprise','rssfeed_public','reminder_public','internet','devicesimcard_pinpuk','computer','slm','statistic',
    'transfer','search_config','document','itiltemplate','ticketrecurrent','recurrentchange','externalevent','reports','group'];
foreach ($zero as $n) { $rights[$n] = 0; }
$rights += [];
$rights['phone'] = READ | UPDATE | CREATE;            // equipos Samsung de la demo (sin borrar)
$rights['infocom'] = READ | UPDATE | CREATE;          // garantía
$rights['dropdown'] = READ | UPDATE | CREATE;         // fabricante, modelos
$rights['state'] = READ | UPDATE | CREATE;            // estados de equipo
$rights['itilcategory'] = READ | UPDATE | CREATE;
$rights['pendingreason'] = READ | UPDATE | CREATE;
$rights['user'] = READ | UPDATE | CREATE;             // clientes ficticios como usuarios (sin borrar, sin import)
$rights['entity'] = READ;
$rights['ticketcost'] = READ | UPDATE | CREATE;
$rights['ticket'] = ($rights['ticket'] ?? 0) | Ticket::ASSIGN;       // la API v2 exige canAssign() para añadir solicitante/técnico al ticket
$rights['ticketvalidation'] = TicketValidation::CREATEREQUEST | TicketValidation::CREATEINCIDENT | TicketValidation::VALIDATEREQUEST | TicketValidation::VALIDATEINCIDENT;
$rights['oauth_client'] = 0; $rights['config'] = 0;
$rights['profile'] = 0;
ProfileRight::updateProfileRights($pid, $rights);
$out['profile'] = ['id' => $pid, 'name' => PROFILE_NAME];

// 3. Usuario de integración
$user = new User();
if (!$user->getFromDBByCrit(['name' => $login])) {
    $uid = $user->add(['name' => $login, 'realname' => 'Integración GSPN', 'firstname' => 'Cuenta', 'password' => $password, 'password2' => $password,
        'authtype' => Auth::DB_GLPI, 'is_active' => 1, 'comment' => 'Cuenta de servicio de la demo. No usar de forma interactiva.', 'entities_id' => 0]);
    if (!$uid) { fwrite(STDERR, "no se pudo crear el usuario\n"); exit(1); }
    $user->getFromDB($uid);
    $out['steps'][] = 'user_created';
} else {
    // Idempotente: no se reescribe la contraseña (la política de historial de GLPI lo rechazaría); solo se asegura activo.
    $user->update(['id' => $user->getID(), 'is_active' => 1]);
    $out['steps'][] = 'user_exists';
}
$uid = (int) $user->getID();
$pu = new Profile_User();
if (!$pu->getFromDBByCrit(['users_id' => $uid, 'profiles_id' => $pid, 'entities_id' => 0])) {
    $pu->add(['users_id' => $uid, 'profiles_id' => $pid, 'entities_id' => 0, 'is_recursive' => 1, 'is_dynamic' => 0]);
}
// quitar otros perfiles que pudieran haberse asignado por defecto (p.ej. Self-Service)
$DB->delete('glpi_profiles_users', ['users_id' => $uid, 'NOT' => ['profiles_id' => $pid]]);
$user->update(['id' => $uid, 'profiles_id' => $pid, 'entities_id' => 0]);
// token de la API heredada (solo para Item_Ticket). getAuthToken() lo crea si no existe y lo reutiliza si ya existe.
$user->getFromDB($uid);
$had_token = !empty($user->fields['api_token']);
// User::prepareInputForUpdate() descarta los campos de token si la sesión activa no es la del propio usuario:
// se actúa temporalmente "como" el usuario de integración (equivale a que él regenere su token en Preferencias).
$_SESSION['glpiID'] = $uid;
$api_token = $user->getAuthToken('api_token', false);
$_SESSION['glpiID'] = 2;
$out['steps'][] = $had_token ? 'legacy_token_exists' : 'legacy_token_generated';
$out['user'] = ['id' => $uid, 'name' => $login, 'api_token' => $api_token];

// 4. Cliente OAuth (API v2)
const CLIENT_NAME = 'Conector Odoo demo (GSPN simulado)';
$client = new OAuthClient();
if (!$client->getFromDBByCrit(['name' => CLIENT_NAME])) {
    $cid = $client->add(['name' => CLIENT_NAME, 'is_active' => 1, 'is_confidential' => 1, 'grants' => ['password'], 'scopes' => ['api'],
        'comment' => 'Cliente OAuth2 de la demo. Grant password con la cuenta de integración.']);
    if (!$cid) { fwrite(STDERR, "no se pudo crear el cliente OAuth\n"); exit(1); }
    $client->getFromDB($cid);
    $out['steps'][] = 'oauth_client_created';
} else {
    $out['steps'][] = 'oauth_client_exists';
}
$out['oauth'] = ['client_id' => $client->fields['identifier'], 'client_secret' => (new GLPIKey())->decrypt($client->fields['secret'])];

// 5. Cliente de la API heredada: el "full access from localhost" por defecto solo acepta 127.0.0.1;
//    con Docker la IP de origen es la del gateway, así que se crea uno sin restricción de IP y sin app_token (queda local por el bind del puerto).
$api = new APIClient();
if (!$api->getFromDBByCrit(['name' => 'Demo GSPN (legacy API, Item_Ticket)'])) {
    $api->add(['name' => 'Demo GSPN (legacy API, Item_Ticket)', 'is_active' => 1, 'entities_id' => 0, 'is_recursive' => 1, 'dolog_method' => 0, 'app_token' => '']);
    $out['steps'][] = 'legacy_apiclient_created';
}
// 6. Técnico ficticio de la demo con perfil Technician. GLPI impide que una cuenta otorgue un perfil con más
//    derechos que el suyo (Profile_User::canCreateItem), así que esta asignación es tarea administrativa, no de la API.
if ($tech_login) {
    $tech = new User();
    if (!$tech->getFromDBByCrit(['name' => $tech_login])) {
        $pw = bin2hex(random_bytes(16)); // no se guarda: el técnico ficticio no inicia sesión
        $tid = $tech->add(['name' => $tech_login, 'realname' => 'Rojas Demo', 'firstname' => 'Carla', 'password' => $pw, 'password2' => $pw,
            'authtype' => Auth::DB_GLPI, 'is_active' => 1, 'comment' => 'Técnica de taller (ficticia, demo).', 'entities_id' => 0]);
        $tech->getFromDB($tid);
        $out['steps'][] = 'tech_user_created';
    }
    $tpu = new Profile_User();
    if (!$tpu->getFromDBByCrit(['users_id' => $tech->getID(), 'profiles_id' => 6, 'entities_id' => 0])) {
        $tpu->add(['users_id' => $tech->getID(), 'profiles_id' => 6, 'entities_id' => 0, 'is_recursive' => 1, 'is_dynamic' => 0]);
        $tech->update(['id' => $tech->getID(), 'profiles_id' => 6]);
        $out['steps'][] = 'tech_profile_assigned';
    }
    $out['technician'] = ['id' => $tech->getID(), 'name' => $tech_login, 'profile' => 'Technician'];
}
echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), "\n";
