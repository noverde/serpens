import cache


class ClsCached:
    counter_cls = 0
    counter_self = 0

    @classmethod
    @cache.cached("test_cache_cls", 900)
    def proc_cls(cls):
        cls.counter_cls += 1
        return cls.counter_cls

    @cache.cached("test_cache_self", 900)
    def proc_self(self):
        self.counter_self += 1
        return self.counter_self
