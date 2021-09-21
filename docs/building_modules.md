# Building and Adding Modules to Hawking

Hawking allows for extending the existing text-to-speech functionality by implementing your own modules. Building them is simple, and getting them hooked up to Hawking is even simpler.

## Building Modules

Hawking modules are just normal classes, with a few extra requirements:

### Inheritance

Hawking modules must inherit from `DiscoverableCog` or `DiscoverableModule`. In short, you're likely just going to want to use the `DiscoverableCog`. The idea of "cogs" comes from [discord.py](https://github.com/Rapptz/discord.py), wherein cogs are just classes that extend upon existing Discord functionality. Modules are basically just normal Pythonic modules, and have no connection to Discord at all. Note that all `DiscoverableCog`s are also `DiscoverableModule`s, but all `DiscoverableModule`s are **not** `DiscoverableCog`s.

For example, if you'd like to add a new command to Hawking that outputs the current time, then you'd have to use `DiscoverableCog`, since your new module needs to hook into the command system.

Note that it's a good idea to pass your module's `__init__` arguments and keyword arguments to the `DiscoverableCog` or `DiscoverableModule` with:

```
super().__init__(*args, **kwargs)
```

### Return Value

Hawking modules must have a `main()` method that returns an instance of `ModuleInitializationStruct`. This is an object that informs the module manager of the basic information it needs to successfully initialize its respective module.

The `ModuleInitializationStruct`'s initialization signature looks like:

```
def __init__(self, cls, is_cog: bool, *init_args, **init_kwargs):
```

You can see that at a minumum, this object requires the class it'll be initializing, and a boolean indicating whether or not it's a cog or not. Additionally, you can provide a list of arguments, and a dict of keyword arguments, which will be supplied to the class during creation.

### Dependencies

Your Hawking module may need to depend on another module to provide certain functionality, and that can be specified in the `ModuleInitializationStruct`, using the `dependencies` keyword argument.

For example, if you've got a module `Foo`, and a cog `Bar` that depends on `Foo`, you might instantiate `Bar`'s `ModuleInitializationStruct` to be something like:

```
ModuleInitializationStruct(Bar, True, dependencies=[Foo.__name__])
```

### After Initialization

`DiscoverableCog` and `DiscoverableModule` offer up some post-initialization methods to explicitly handle both success and failure states during module creation. There's the `afterSuccessfulInit` and `afterFailedInit`, which both define a function that will be executed either upon success or failure of initialization, respectively.

They've also got an optional boolean `successful` property, which can be set inside the child module to alert subscribers that it was successfully initialized or not. This property being set defines which post-initialization function is called.

For example, these post-initialization actions can be added to a module via it's `ModuleInitializationStruct` like so:

```
ModuleInitializationStruct(Bar, True, afterSuccessfulInit=lambda: print('Module initialized successfully!'))
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

Module specific configuration files can be loaded via the `load_module_config` function in [utilities.py](https://github.com/naschorr/hawking/blob/master/code/common/utilities.py), which just takes a path to a directory containing the `config.json` file. It returns a `dict` corresponding to the key-value pairs inside the module configuration file, and the global Hawking `config.json` file (with the module's configuration file taking precendence, so be careful!). It can be invoked like so:

```
from common import utilities

config = utilities.load_module_config(Path(__file__).parent)
```

## Practical Examples

Check out the [Fortune](https://github.com/naschorr/hawking/blob/master/modules/fortune/fortune.py) module for a simple, self contained example that adds a single command. There's also the [Stupid Questions](https://github.com/naschorr/hawking/blob/master/modules/stupid_questions/stupid_questions.py) and [Reddit](https://github.com/naschorr/hawking/blob/master/modules/reddit/reddit.py) modules which illustrate both dependency management, as well as module configuration. There's also a practical example of the `afterSuccessfulInit` in use for the [Audio Player](https://github.com/naschorr/hawking/blob/master/code/common/audio_player.py) module inside [`hawking.py`](https://github.com/naschorr/hawking/blob/master/code/hawking.py).
