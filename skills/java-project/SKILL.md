---
name: java-project
description: "Read a Java project — a repository URL or a folder — as a graph: its Maven modules, resolved dependency tree, managed versions, types, members, annotations, imports and config settings, each linked to the line. Use when someone asks about the structure, dependencies or code of a specific Java project."
---

# Reading a Java project

A project is named by a **key**: `https://github.com/acme/shop` (default branch), `…@v2.1`
(a tag, branch or commit), or a folder (`shop` in the owner's mounted workspace, or a path under
the world's `data/`). Pass it unchanged to every view as `project`.

Start with `ProjectOverview` — it proves the key resolves and says which commit was read. Then:

| Question | View |
|---|---|
| What modules does it have? | `ProjectModules` |
| What is annotated with X? | `AnnotatedWith` (`annotation`: the simple name) |
| Where is package/API X still used? | `UsesOfPackage` (`prefix`) |
| Where is setting X set, and to what? | `SettingsNamed` (`prefix`) |
| Why is library X in my build? | `WhyIsItHere` (`artifact`) |
| Which version of X do I get, and who pinned it? | `VersionOf` (`artifact`) |
| The full tree of a module | `DependencyTree` (`module`, '' for the root) |

For anything else, query the graph from `(p:JavaProject {key: $project})` — see the realm's
types for the hops. Always quote `link` when you cite code: it is the exact line, at the commit read.

Say what you could not see: a module whose POM is missing, a file that does not parse, a
sibling module not found — these come back as diagnostics, not as empty answers.
