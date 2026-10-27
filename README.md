# realm-java-project

A Java project — yours — as a graph you can query, read where it lives when a question reaches it.
Its Maven build (every module, the dependency tree Maven resolves, the versions its BOMs pin) and its
own source (every type, member, annotation and import, and every setting in its `.properties` and YAML
files), each linked to the exact line. Nothing is ingested and nothing is stored.

```cypher
MATCH (p:JavaProject {key: 'https://github.com/spring-projects/spring-petclinic'})-[:HAS_ANNOTATION]->(a:JavaProjectAnnotation {name: 'Transactional'})
RETURN a.targetName, a.attributes, a.link
```

## Naming a project

| key | read from |
|---|---|
| `https://github.com/acme/shop` | the default branch, at the commit it points to now |
| `https://github.com/acme/shop@v2.1` | a tag, branch or commit |
| `shop` | a folder in the workspace the appliance owner mounted (`embabel workspace use ~/code`) |
| `projects/shop` | a folder under the world's `data/` |

Public repositories only, for now. A commit is read once and kept; a folder is read afresh.

## Views

`ProjectOverview`, `ProjectModules`, `AnnotatedWith`, `UsesOfPackage`, `SettingsNamed`, `WhyIsItHere`,
`VersionOf`, `DependencyTree` — see `views/project.yml`. Every type and hop is in `types/project.yml`.

It knows no framework: an annotation is its name and attributes as written. `realm-spring` gives them meaning.

Requires an Embabel appliance with the `source` and `maven` producer kinds' `from: project`.
Java source only; Kotlin is not read yet.
