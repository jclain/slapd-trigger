# slapd-trigger.py

`slapd-trigger.py` est un serveur attaquable par l'overlay back-sock de slapd
pour déclencher des actions sur certains types de modification

## Installation

slapd-trigger.py a été écrit et testé sous Python 2.6 uniquement. Il devrait
fonctionner avec Python 2.7, mais il est à peu près sûr qu'il ne fonctionne pas
avec Python 3.x

La seule librairie requise est [python-ldap](http://...)

Ensuite, il faut lancer le script setup.py pour faire l'installation proprement
dite.
~~~
$ sudo python setup.py install
~~~

* Par défaut, le script `slapd-trigger.py` est installé dans `/usr/local/bin`
* De plus, un fichier de configuration par défaut `slapd-trigger.rules` est
  installé dans `/etc/ldap`
* Un script de démarrage `slapd-trigger` est installé dans `/etc/init.d`

## Démarrage rapide

Editer le fichier de configuration `/etc/ldap/slapd-trigger.rules` et s'assurer
que le contenu ressemble à celui ci-dessous. La variable `suffix` défini le
suffixe de base pour la base de données LDAP.
~~~
logfile /var/log/slapd-trigger.log
loglevel INFO
pidfile /var/run/slapd-trigger.pid
socket_path /var/run/slapd-trigger.sock
socket_owner openldap:
socket_mode 660
server ldapi:// saslmech=EXTERNAL
var suffix dc=univ-reunion,dc=fr

match-dn: ou=People,${suffix}
match-modify: cn
cn: (\S+)(?:\s*(.+))?
-
replace: sn
sn: \1
-
replace: givenName
givenName: \2
-
replace: displayName
displayName: \2 \1
-
~~~
Cette configuration indique que lorsqu'une modification de cn est effectuée, il
faut mettre à jour en conséquence les valeurs de sn, givenName et displayName.
La correspondance est faite avec une expression, régulière, et les valeurs des
groupes sont extraits pour mettre à jour les attributs.

Démarrer le service
~~~
$ sudo service slapd-trigger start
~~~

Configurer back-sock sur la base de données `{1}mdb`
NB: si la base de données principale est différente, e.g `{2}mdb` ou `{1}hdb`,
corriger les commandes en conséquence.
~~~
$ sudo ldapmodify -H ldapi:// -Y EXTERNAL <<EOF
dn: cn=module{0},cn=config
changetype: modify
add: olcModuleLoad
olcModuleLoad: back_sock.la
-
EOF

$ sudo ldapmodify -H ldapi:// -Y EXTERNAL <<EOF
dn: olcOverlay=sock,olcDatabase={1}mdb,cn=config
changetype: add
objectClass: olcConfig
objectClass: olcOverlayConfig
objectClass: olcOvSocketConfig
olcOverlay: sock
olcDbSocketPath: /var/run/slapd-trigger.sock
olcOvSocketOps: modify modrdn add delete
EOF
~~~

Faire une modification et vérifier le résultat. On part du principe que l'objet
uid=jdoe,ou=People,dc=univ-reunion,dc=fr existe:
~~~
$ ldapsearch -LLL -H ldapi:// -x -b ou=People,dc=univ-reunion,dc=fr '(uid=jdoe)' cn sn givenName displayName
dn: uid=jdoe,ou=People,dc=univ-reunion,dc=fr
cn: Doe John
sn: Doe
givenName: John
displayName: John Doe

$ sudo ldapmodify -H ldapi:// -Y EXTERNAL <<EOF
dn: uid=jdoe,ou=People,dc=univ-reunion,dc=fr
changetype: modify
replace: cn
cn: GI Joe
-
EOF

$ ldapsearch -LLL -H ldapi:// -x -b ou=People,dc=univ-reunion,dc=fr '(uid=jdoe)' cn sn givenName displayName
dn: uid=jdoe,ou=People,dc=univ-reunion,dc=fr
cn: GI Joe
sn: GI
givenName: Joe
displayName: Joe GI
~~~

Note: il est aussi possible de lancer la mise à jour avec l'état "setup" du
fichier de configuration. Par défaut, les règles suivantes figurent dans le
fichier de configuration:
~~~
# Initialisation and configuration
match-state: setup
dn: cn=module{0},cn=config
changetype: modify
add: olcModuleLoad
olcModuleLoad: back_sock.la
-

match-state: setup
dn: olcOverlay=sock,olcDatabase=${maindb},cn=config
changetype: add
objectClass: olcConfig
objectClass: olcOverlayConfig
objectClass: olcOvSocketConfig
olcOverlay: sock
olcDbSocketPath: ${socket_path}
olcOvSocketOps: modify modrdn add delete
~~~

Ainsi, les commandes de configuration plus haut auraient pû être exécutées de la
manière suivante:
~~~
$ sudo slapd-trigger.py -v "maindb={1}mdb" --run-state setup
~~~

## Usage

L'aide peut être affichée avec `slapd-trigger.py --help`:
~~~
Usage: 
	slapd-trigger.py

Options:
  -h, --help            show this help message and exit
  -L LOGFILE, --logfile=LOGFILE
                        Spécifier l'emplacement du fichier de logs.
  -d LOGLEVEL, --loglevel=LOGLEVEL
                        Spécifier le niveau de logs qui sont enregistrés
                        (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --pidfile=PIDFILE     Spécifier l'emplacement du fichier de pid.
  -s SOCKET_PATH, --socket-path=SOCKET_PATH
                        Spécifier l'emplacement du fichier de socket.
  --socket-owner=SOCKET_OWNER
                        Spécifier le propriétaire du fichier de socket.
  --socket-mode=SOCKET_MODE
                        Spécifier le mode du fichier de socket.
  -c CONFIG, --config=CONFIG
                        Spécifier le fichier de configuration. Par défaut
                        prendre le fichier de même nom de base que ce script
                        avec l'extension .rules
  -v NAME=VALUE, --var=NAME=VALUE
                        (Re)définir une variable

  Options de connexion:
    -H LDAPURI, --ldapuri=LDAPURI
                        LDAP URI of the server
    -x, --simpleauth    Use simple authentication
    -D BINDDN, --binddn=BINDDN
                        Bind DN for simple authentication
    -w CREDENTIALS, --password=CREDENTIALS
                        Credentials
    -Y SASLMECH, --saslmech=SASLMECH
                        SASL mechanism
    -U AUTHCID, --authcid=AUTHCID
                        SASL authentication identity
    -X AUTHZID, --authzid=AUTHZID
                        SASL authorization identity
    -R REALM, --realm=REALM
                        SASL realm

  Options avancées:
    --logformat=LOGFORMAT
                        Spécifier le format des lignes de logs.
    --devel             Activer le mode développement: les données sont lues
                        sur STDIN, le résultat affiché sur STDOUT, et les logs
                        sur STDERR. En mode développement, les options
                        --logfile, --socket-path, --socket-owner sont ignorées
    --devel-input=INPUT
                        En mode développement, lire les données depuis le
                        fichier spécifié
    --devel-output=OUTPUT
                        En mode développement, écrire les données dans le
                        fichier spécifié
    --devel-ldif-output=LDIF-OUTPUT
                        En mode développement, écrire les données au format
                        LDIF dans le fichier spécifié au lieu de mettre à jour
                        le serveur LDAP
    --run-state=STATE   Lancer le traitement correspondant à l'état spécifié.
    --no-init           Désactiver le traitement de l'état 'init'. A utiliser
                        avec --run-state pour être sûr de ne lancer que les
                        actions de l'état spécifié.
~~~

## Configuration

Un fichier du même nom de base que le script (e.g `slapd-trigger.rules`) est
cherché d'abord dans le même répertoire que le script, puis dans `/etc/ldap`

Ce fichier contient d'abord des directives de configuration, sous la forme de
lignes `name value`, puis les règles sont exprimées au format LDIF.

`logfile`
: Emplacement du fichier de log, ou `-`, `/dev/stdout` ou `/dev/stderr` pour
  écrire sur la sortie standard

`loglevel`
: Niveau de logs, parmi TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL, ou sous
  forme numérique

`logformat`
: Format des lignes de log. Consulter la documentation du module `logging` pour
  les détails. La valeur par défaut est `%(levelname)s %(asctime)s %(message)s`

`pidfile`
: Emplacement du fichier de PID

`socket_path`
: Emplacement du fichier de socket à créer

`socket_owner`
: Changer le propriété du fichier de socket après sa création à la valeur
  spécifiée, de la forme `user[:group]`

`socket_mode`
: Changer le mode du fichier de socket après sa création à la valeur spécifiée
  sous forme numérique, e.g. `660`

`server`
: Spécification de connexion au serveur pour la mise à jour des données, sous la
  forme d'une ligne ressemblant à une directive syncrepl,
  e.g `ldapuri bindmethod=simple binddn= credentials=`
  ou `ldapuri bindmethod=sasl saslmech= authcid= authzid= realm= credentials=`
  La valeur par défaut est `ldapi:// saslmech=EXTERNAL`

Voici un exemple de la section configuration:
~~~
logfile /var/log/slapd-trigger.log
loglevel INFO
pidfile /var/run/slapd-trigger.pid
socket_path /var/run/slapd-trigger.sock
socket_owner openldap:
socket_mode 660
server ldapi:// saslmech=EXTERNAL
~~~

## Règles de mise à jour

Les règles sont écrite au format LDIF. Chaque règle est composée d'une partie
"correspondance", qui permet de vérifier le type de modification qui est
notifiée par back-sock. Si toutes les règles de correspondance sont satisfaites,
alors la partie "modification" est appliquée. La "modification" suit directement
la partie correspondance et décrit au format LDIF les modifications à apporter à
l'objet.

### Sélection des objets sources

Chaque groupe de correspondance au sein d'un règle commence par une ligne de la
forme `match-xxx:`. Certaines directives prennent des valeurs. Ces règles de
correspondance sont vérifiées par rapport à l'objet fourni par back-sock.

Pour que la partie modification soit considérée:
* Si plusieurs directives `match-xxx` sont spécifiées, elles doivent TOUTES
  correspondre
* Si au sein d'une directive `match-xxx` plusieurs valeurs sont spécifiées, elle
  doivent TOUTES correspondre

`match-dn[.DNSTYLE]: DN`
: Vérifier que le DN de l'objet modifié correspond au DN spécifié.

  DNSTYLE spécifie le type de correspondance à faire sur le DN de l'objet
  modifié, et peut valoir `exact`, `base[object]`, `regex`, `one[level]`,
  `sub[tree]` ou `children`. Par défaut, DNSTYLE vaut `subtree`.

  Par exemple, les deux lignes suivantes sont équivalentes:
  ~~~
  match-dn.regex: .+,ou=People,dc=univ-reunion,dc=fr
  match-dn.children: ou=People,dc=univ-reunion,dc=fr
  ~~~

`match-state: STATE`
: Vérifier que l'état courant est celui spécifié. Les états valides sont
  `setup`, `init`, `before_start`, `after_start`, `before_stop`.

  * L'état `setup` n'est atteint que manuellement, avec l'option --run-state
  * L'état `init` est activé après la lecture du fichier de configuration
  * L'état `before_start` est activé avant que le script ne démarre l'écoute sur
    le socket et le thread de travail. L'alias `start` est accepté aussi.
  * L'état `after_start` est activé après que le serveur écoute sur le socket
    et est pleinement opérationnel. L'alias `started` est accepté aussi.
  * L'état `before_stop` est activé avant que le serveur ne s'arrête. L'alias
    `stop` est accepté aussi.

`match-PARAM: VALUE`

: Vérifier que le paramètre PARAM vaut VALUE. Les paramètres sont les lignes
  d'information fournies par back-sock. NAME peut valoir `operation`, `msgid`,
  `suffix`, `changetype`. En fonction de la façon dont back-sock est configuré,
  il est possible d'avoir aussi `binddn`, `peername`, `ssf`, `connid`.

  * Le paramètre `operation` peut valoir ADD, DELETE, MODIFY, MODRDN
  * Le paramètre `changetype` peut valoir add, delete, modify, modrdn

`match-OP: ATTR`
: Pour le paramètre `changetype: modify`, vérifier qu'il existe le type
  d'opération spécifié pour l'attribut spécifié. `OP` peut valoir `add`,
  `replace`, `delete`, `modify`, `any`

  * Les opérations `add`, `replace` et `delete` sont les opérations standard de
    LDAP.
  * L'opération `modify` signifie `add` OU `replace`
  * L'opération `any` signifie n'importe quelle opération: `add` OU `replace` OU
    `delete`

  ATTR est un nom d'attribut. Cette ligne peut être suivie de lignes de
  correspondance pour l'attribut.

`ATTR[.VALTYPE]: VALUE`
: Cette ligne de correspondance peut figurer après une ligne de type `match-OP:`
  et permet de vérifier la valeur d'un attribut modifié.

  VALTYPE spécifie le type de correspondance à faire sur la valeur de l'attribut
  modifié, et peut valoir `exact` ou `regex`. Par défaut, VALTYPE vaut `regex`.

Par exemple, la règle suivante est activée pour toute modification de l'attribut
cn sur un objet de la branche ou=People,dc=univ-reunion,dc=fr. Pour l'exemple,
on requière aussi que la modification doivent porter sur une valeur qui commence
par "Mister "
~~~
match-dn.children: ou=People,dc=univ-reunion,dc=fr
match-modify: cn
cn: Mister .*
~~~

Dès qu'une ligne qui n'est pas d'une des formes précédente est rencontrée,
l'analyse des règles de correspondance s'arrête, et l'on passe à l'analyse des
règles de modification.

### Modifications à appliquer

Les règles de modifications sont écrites dans le format attendu par ldapmodify.
* `dn:` peut être omis et vaut par défaut le DN de l'objet pour lequel on reçoit
  la notification.
* `changetype:` peut être omis et vaut par défaut `modify`

Dans les règles de correspondance qui utilisent des expressions régulières, il
est possible d'utiliser des groupes. Lorsqu'il y a une correspondance, la valeur
du groupe est enregistrée et peut être réutilisée avec l'une des syntaxes `\N`
ou `\g<NAME>`, où N est le numéro incrémental du groupe, et NAME le nom d'un
groupe nommé.

Les variables définies peuvent être utilisées avec la syntaxe `${name}` dans les
règles de modification, mais aussi dans les règles de correspondance.

Voici un exemple d'utilisation des groupes et des variables dans les règles de
correspondance et les règles de modification:
~~~
...
var prefix dc=univ-reunion,dc=fr
...

match-dn: ${prefix}
match-modify: cn
cn: (\w+)\s*(\w+)
changetype: modify
replace: displayName
displayName: \2 \1
add: description
description: Modification dans ${prefix}
~~~

Dans l'exemple suivant, la modification du cn d'un objet provoque la mise à jour
d'un objet correspondant dans une autre branche:
~~~
match-dn.regex: uid=([^,]+),ou=Src,dc=univ-reunion,dc=fr
match-modify: cn
cn: (.*)
dn: uid=\1,ou=Dest,dc=univ-reunion,dc=fr
replace: cn
cn: \2
~~~

-*- coding: utf-8 mode: markdown -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8:noeol:binary