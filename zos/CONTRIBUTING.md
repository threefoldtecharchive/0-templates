## Naming conventions

To keep the code-base clean and consistent, please follow the following conventions.

### Schemas

- Use the template name when referring to another service in a schema field.

```capnp
struct Schema {
    node @0: Text; # pointer to the node the hyperviser is running on
    vm @1: Text; # pointer to the vm service managing this hyperviser
}
```

- Use camelcase for schema fields.

```capnp
struct Schema {
    hostNetworking @0: Text;
}
```

### Templates

Use template name for service instances.

```python
 container = self.api.services.create(CONTAINER_TEMPLATE_UID, name, args)

```

Use <template>_sal for sal variables.
```python
node_sal = j.clients.zero_os.sal.node_get("bootstrap")

```

## Documentation
Every new template should be accompanied by a README.md explaining the different fields of the schema, the available actions and any other information that might help the user.
The documentation should also include the following examples:

    1. Usage example via the 0-robot DSL

    2. Usage example via the 0-robot CLI

Please use other documentation as a reference.


## Tests
Every new template should be accompanied by a test file. Please use other tests as a reference.




## Templates checklist
After creating/editing a template, please go through this checklist before creating a PR:

- [ ] Template code follows naming [conventions](#naming-conventions).
- [ ] Unittests for the template are up-to-date with the changes in the PR.
- [ ] The template should have the basic expected actions if applicable (install, uninstall, start, stop, upgrade, monitor).
- [ ] [README.md](#documentation) is present for the template and modified according to new changes.
- [ ] Any repitive/management code should be added to the sal.