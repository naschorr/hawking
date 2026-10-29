# Building and Adding Modules to Hawking

Hawking allows for extending the existing text-to-speech functionality by implementing your own modules. Building them is simple, and getting them hooked up to Hawking is even simpler.

## Building Modules

Hawking addons are normal Python packages under `code/addons/<addon_name>/`. Each package provides a same-named entrypoint file, such as `code/addons/fortune/fortune.py`, with a `main()` function. The reusable module lifecycle and Discord abstractions live under `code/hawking/core/`.

### Inheritance

Hawking addons must inherit from either `DiscoverableCog` or `DiscoverableModule` (see [`discoverable_module.py`](https://github.com/naschorr/hawking/blob/master/code/hawking/core/services/module_manager/discoverable_module.py) and [`module.py`](https://github.com/naschorr/hawking/blob/master/code/hawking/core/services/module_manager/module.py)). In short, you're likely just going to want to use `DiscoverableCog`. The idea of "cogs" comes from [discord.py](https://github.com/Rapptz/discord.py), wherein cogs are classes that extend Discord functionality. Modules are normal Python classes with no direct connection to Discord. All `DiscoverableCog`s are also `DiscoverableModule`s, but not vice versa.

For example, if you'd like to add a new command to Hawking that outputs the current time, then you'd have to use `DiscoverableCog`, since your new module needs to hook into the command system.

Note that it's a good idea to pass your module's `__init__` arguments and keyword arguments to the `DiscoverableCog` or `DiscoverableModule` with:

```
super().__init__(*args, **kwargs)
```

### Return Value

Hawking modules must have a `main()` method that returns an instance of `ModuleInitializationContainer`. This is an object that informs the module manager of the basic information it needs to successfully initialize its respective module.

The `ModuleInitializationContainer`'s initialization signature looks like:

```
def __init__(self, cls, *init_args, **init_kwargs):
```

You can see that at a minumum, this object requires the class it'll be initializing, and a boolean indicating whether or not it's a cog or not. Additionally, you can provide a list of arguments, and a dict of keyword arguments, which will be supplied to the class during creation.

### Dependencies

Your Hawking module may need to depend on another module to provide certain functionality, and that can be specified in the `ModuleInitializationContainer`, using the `dependencies` keyword argument.

For example, if you've got a module `Foo`, and a cog `Bar` that depends on `Foo`, you might instantiate `Bar`'s `ModuleInitializationContainer` to be something like:

```
ModuleInitializationContainer(Bar, dependencies=[Foo])
```

## Configuration

Hawking modules requiring external configuration can easily do so with a simple JSON file, and the module config loader function.

The configuration file is just a normal JSON file, with a root JSON object containing all of key-value pairs used to pass data to the module. For example:

```
{
    "search_url": "https://duckduckgo.com/",
    "api_version": "v2",
    "api_token": "73b9bb61-f270-485b-aa13-184cf86c5ea1"
}
```

Built-in module configuration is defined by Pydantic models under `modules`. Addon settings live under the separate, optional `addons` object (for example, `addons.reddit`). The core treats addon entries as opaque data. An addon may declare its own Pydantic config model through `ModuleInitializationContainer(config_model=...)`; the module manager validates that addon's section and passes the typed result to its constructor. If validation fails, only that addon is skipped. Addons without a declared config model receive their section as a dictionary, or an empty dictionary when no section is configured.

## Practical Examples

Check out the [Fortune](https://github.com/naschorr/hawking/blob/master/code/addons/fortune/fortune.py) addon for a simple, self-contained example that adds a single command. The [Stupid Questions](https://github.com/naschorr/hawking/blob/master/code/addons/stupid_questions/stupid_questions.py) and [Reddit](https://github.com/naschorr/hawking/blob/master/code/addons/reddit/reddit.py) addons also illustrate dependency management and module configuration.
