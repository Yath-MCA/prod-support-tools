# Tabs package for IMPACT ConfigSuite
from .analyses_tab import AnalysesTab
from .patterns_tab import PatternsTab
from .search_tab import SearchTab
from .data_transfer_tab import DataTransferTab
from .impact_to_ceg_tab import ImpactToCEGTab
from .pgm_processor_tab import PGMProcessorTab
from .word_extractor_tab import WordExtractorTab
from .id_pattern_extractor_tab import IDPatternExtractorTab
from .citation_pattern_extractor_tab import CitationPatternExtractorTab
from .new_config_tab import NewConfigTab
from .compare_tab import HTMLCompareTab, HTMLCompareReplaceTab
from .element_extractor_tab import ElementExtractorTab
from .xml_compare_tab import XMLCompareTab
from .document_manager_tab import DocumentManagerTab

__all__ = [
    "AnalysesTab",
    "PatternsTab",
    "SearchTab",
    "DataTransferTab",
    "ImpactToCEGTab",
    "PGMProcessorTab",
    "WordExtractorTab",
    "IDPatternExtractorTab",
    "CitationPatternExtractorTab",
    "NewConfigTab",
    "HTMLCompareTab",
    "HTMLCompareReplaceTab",
    "ElementExtractorTab",
    "XMLCompareTab",
    "DocumentManagerTab",
]
