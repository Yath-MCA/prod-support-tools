from metadata_harvester.service.geo.sources.base import LocationRecord, Source
from metadata_harvester.service.geo.sources.openalex import OpenAlexSource
from metadata_harvester.service.geo.sources.ror import RorSource

DEFAULT_SOURCES: dict[str, Source] = {
    "ror": RorSource(),
    "openalex": OpenAlexSource(),
}

__all__ = ["LocationRecord", "Source", "DEFAULT_SOURCES", "RorSource", "OpenAlexSource"]
