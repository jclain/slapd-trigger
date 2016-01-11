# TODO

Implémenter la non correspondance des expressions régulières

Vérifier que le remplacement des variables est fait dans les correspondances sur
les valeurs.

`match-PARAM: VALUE`
: Ajouter VALTYPE parmi exact, expr, regex
  expr permet d'avoir une expression de la forme OP VALUE, e.g
  =value        égalité
  ~regex        expression régulière
  !=value       non égalité
  !~regex       expression régulière avec correspondance inversée
  <value        comparaison entière ou lexicale
  >value
  !<value
  !>value
  Ajouter aussi le VALTYPE expr pour les valeurs des attributs

`match-defined: NAMES...`
: S'assurer que les variables spécifiées ont une valeur définie

`match-present: ATTRS...`
: S'assurer que les attributs spécifiés existent

`match-absent: ATTRS...`
: S'assurer que les attributs spécifiés n'existent pas

`match-filter: FILTER...`
: Vérifier que l'objet correspond au filtre spécifié

`before-match: ACTION`
`after-match: ACTION`
: Faire une action avant de vérifier si l'objet entrant correspond à la règle,
  ou après que l'objet corresponde à la règle

En plus de ${var}, ajouter la syntaxe $(func) qui permet d'évaluer une
expression python. Il faudra sans doute définir un protocole pour définir des
fonctions utilisateurs.

Il faudrait que l'on puisse accéder aux valeurs des attributs par une syntaxe du
genre ${ATTR} pour tout l'attribut ou ${ATTR[0]} pour une valeur précise pour un
attribut multivalué.
On pourrait aussi préfixer l'attribut comme ceci ${attrs.ATTR}, ce qui serait
cohérent avec l'utilisation dans une expression, ou attrs serait un dictionnaire
qui supporte l'accès par __getattr__ et __getitem__

Quand on écrit `attr: ${value}` et que value s'avère être une liste, faire
autant de lignes `attr:` que de valeurs. Pour joindre ou splitter les valeurs,
il faut une expression, par exemple `$(','.join(attrs.ATTR))` ou
`$(attrs.ATTR[0].split(","))`

# ACTION

`ensure-attrs ATTRS...`
: Vérifier qu'il y a au moins une occurence de chaque attribut dans l'objet
  obtenu. Sinon faire une recherche pour récupérer la valeur courante des
  attributs manquants

`search-attrs ATTRS...`
: Faire une recherche pour récupérer la valeur courante des attributs
  spécifiés. La valeur initiale éventuellement obtenue est écrasée

# SCOPES

`scope: global`
: les règles spécifiées s'ajoutent à toutes les règles définies dans le
  fichier. Au moins une des règles de scope global doit correspondre pour que
  les règles soient examinées

`scope: NAME`
: les règles spécifiées sont nommées NAME

`match-scope: NAME`
: S'assurer que l'une des règles du scope spécifié correspond. Toutes les
  règles contiennent implicitement `match-scope: global`

OU:

`scope: local`
: les règles spécifiées s'ajoutent à toutes les règles définies jusqu'au
  prochain `scope: local`. Au moins une de ces règles doit correspondre pour
  que les règles suivantes soient examinées.

-*- coding: utf-8 mode: markdown -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8:noeol:binary