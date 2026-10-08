"""Web page backends."""

from neteyes.backends.web.trafilatura_backend import TrafilaturaBackend
from neteyes.backends.web.jina_backend import JinaReaderBackend
from neteyes.backends.web.readability_backend import DirectReadabilityBackend

__all__ = ["TrafilaturaBackend", "JinaReaderBackend", "DirectReadabilityBackend"]
