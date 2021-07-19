from inspect import isclass

class ModuleInitializationStruct:
    def __init__(self, cls, is_cog: bool, *init_args, **init_kwargs):
        if(not isclass(cls)):
            raise RuntimeError("Provided class parameter '{}' isn't actually a class.".format(cls))

        self.cls = cls
        self.is_cog = is_cog
        self.init_args = init_args
        self.init_kwargs = init_kwargs

        ## Does the module require a root
        self.use_root_instance = init_kwargs.get('use_root_instance', True)
        self.use_bot_instance = init_kwargs.get('use_bot_instance', True)

        ## Don't pass these along to invoked modules
        if ('use_root_instance' in init_kwargs):
            del init_kwargs['use_root_instance']
        if ('use_bot_instance' in init_kwargs):
            del init_kwargs['use_bot_instance']
