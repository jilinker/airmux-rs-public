"""Shared strict, private YAML reader used by deployment tools."""
import os
import tempfile
from pathlib import Path
import yaml

class Loader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError('configuration keys must be unique strings')
            result[key] = self.construct_object(value_node, deep=deep)
        return result

def load_config(path, private=True):
    path = Path(path)
    metadata = path.stat()
    if not path.is_file() or metadata.st_size > 1024 * 1024:
        raise ValueError('config.yaml must be a regular file smaller than 1 MiB')
    if private and os.name == 'posix' and metadata.st_mode & 0o077:
        raise ValueError('config.yaml contains secrets; run chmod 600 on the file')
    try:
        data = yaml.load(path.read_text(encoding='utf8'), Loader=Loader)
    except Exception:
        raise ValueError('invalid config.yaml syntax or duplicate keys') from None
    if not isinstance(data, dict):
        raise ValueError('config.yaml must contain one mapping document')
    return data

def atomic_write(path, text, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'w', encoding='utf8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
