'''Utitlities used accross the extension.
'''

class monkey_patch:

    def __init__(self, obj, prop, patch_with):
        self.obj = obj
        self.prop = prop
        self.patch_with = patch_with

    def __call__(self, method):
        original_prop = None
        if hasattr(self.obj, self.prop):
            original_prop = getattr(self.obj, self.prop)

        def _with_patched(*args, **kwargs):
            # patch
            setattr(self.obj, self.prop, self.patch_with)
            try:
                return method(*args, **kwargs)
            finally:
                # unpatch
                if original_prop is not None:
                    setattr(self.obj, self.prop, original_prop)
                else:
                    delattr(self.obj, self.prop)
        _with_patched.__name__ = method.__name__
        _with_patched.__module__ = method.__module__
        _with_patched.__doc__ = method.__doc__
        return _with_patched