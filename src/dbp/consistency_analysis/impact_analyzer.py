###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the ConsistencyImpactAnalyzer class, which analyzes how detected
# inconsistencies impact the overall project. It leverages the doc_relationships
# component to understand document interdependencies and enhances consistency
# reports with impact information.
###############################################################################
# [Source file design principles]
# - Integrates with the doc_relationships component but maintains separation of concerns
# - Uses document relationship graph to determine propagation of inconsistency impacts
# - Enhances ConsistencyReport objects with impact analysis data
# - Follows the "high cohesion, low coupling" principle in its interactions
###############################################################################
# [Source file constraints]
# - Depends on doc_relationships component for relationship data
# - Operates on ConsistencyReport and InconsistencyRecord objects
# - Must maintain proper separation between consistency analysis and document relationships
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T23:14:45Z : Initial implementation of ConsistencyImpactAnalyzer by CodeAssistant
# * Added integration with doc_relationships component
# * Implemented analyze_impact method for enhancing consistency reports
###############################################################################

import logging
from typing import Optional, List, Dict, Any

# Import from consistency_analysis
from .data_models import ConsistencyReport, InconsistencyRecord

# Import from doc_relationships
from ..doc_relationships.component import DocRelationshipsComponent

logger = logging.getLogger(__name__)

class ConsistencyImpactAnalyzer:
    """
    Analyzes the impact of detected inconsistencies on the overall project
    documentation and code base using document relationship data.
    """
    
    def __init__(self, doc_relationships_component: DocRelationshipsComponent, 
                 logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ConsistencyImpactAnalyzer.
        
        Args:
            doc_relationships_component: Component that provides document relationship information
            logger_override: Optional logger instance
        """
        self.doc_relationships = doc_relationships_component
        self.logger = logger_override or logger
        self.logger.debug("ConsistencyImpactAnalyzer initialized")
        
    def analyze_impact(self, report: ConsistencyReport) -> None:
        """
        Analyze the impact of inconsistencies in the report and enhance the
        report with impact information.
        
        Args:
            report: The consistency report to analyze and enhance
            
        Side effects:
            Modifies the report in place, adding impact data to its metadata
        """
        self.logger.info(f"Analyzing impact for consistency report {report.id}")
        
        # Initialize impact data structure in report metadata
        if 'impact' not in report.metadata:
            report.metadata['impact'] = {
                'affected_documents': set(),
                'propagation_paths': [],
                'severity_amplification': {},
                'summary': {}
            }
        
        # Process each inconsistency in the report
        for inconsistency in report.inconsistencies:
            self._analyze_inconsistency_impact(inconsistency, report)
            
        # Convert set to list for JSON serialization
        report.metadata['impact']['affected_documents'] = list(
            report.metadata['impact']['affected_documents']
        )
        
        # Generate impact summary
        self._generate_impact_summary(report)
        
        self.logger.info(f"Impact analysis complete for report {report.id}. "
                        f"Identified {len(report.metadata['impact']['affected_documents'])} affected documents.")
        
    def _analyze_inconsistency_impact(self, inconsistency: InconsistencyRecord, 
                                     report: ConsistencyReport) -> None:
        """
        Analyze the impact of a single inconsistency and update the report metadata.
        
        Args:
            inconsistency: The inconsistency record to analyze
            report: The report to update with impact data
        """
        try:
            # Use doc_relationships component to find impacts
            impacts = self.doc_relationships.analyze_document_impact(inconsistency.source_file)
            
            # Add the source and target files to affected documents
            report.metadata['impact']['affected_documents'].add(inconsistency.source_file)
            if inconsistency.target_file:
                report.metadata['impact']['affected_documents'].add(inconsistency.target_file)
                
            # Add document impacts from the relationship analysis
            for impact in impacts:
                report.metadata['impact']['affected_documents'].add(impact.target_document)
                
                # Record propagation path
                path = {
                    'source': inconsistency.source_file,
                    'inconsistency_id': inconsistency.id,
                    'affected_document': impact.target_document,
                    'relationship_type': impact.relationship_type,
                    'impact_level': impact.impact_level
                }
                report.metadata['impact']['propagation_paths'].append(path)
                
                # Calculate severity amplification based on relationship importance
                if inconsistency.id not in report.metadata['impact']['severity_amplification']:
                    report.metadata['impact']['severity_amplification'][inconsistency.id] = {
                        'original_severity': inconsistency.severity.value,
                        'amplified_by': []
                    }
                
                # Record amplification factors from the dependency chain
                if impact.impact_level == 'high':
                    report.metadata['impact']['severity_amplification'][inconsistency.id]['amplified_by'].append({
                        'document': impact.target_document,
                        'reason': f"High impact on dependent document via {impact.relationship_type}"
                    })
        
        except Exception as e:
            self.logger.error(f"Error analyzing impact for inconsistency {inconsistency.id}: {e}", 
                             exc_info=True)
    
    def _generate_impact_summary(self, report: ConsistencyReport) -> None:
        """
        Generate an impact summary for the report based on the collected impact data.
        
        Args:
            report: The report to update with impact summary
        """
        affected_count = len(report.metadata['impact']['affected_documents'])
        propagation_count = len(report.metadata['impact']['propagation_paths'])
        
        # Generate summary statistics
        report.metadata['impact']['summary'] = {
            'total_affected_documents': affected_count,
            'propagation_count': propagation_count,
            'amplification_count': sum(1 for inc_id, amp in 
                                      report.metadata['impact']['severity_amplification'].items() 
                                      if amp['amplified_by']),
            'max_propagation_depth': self._calculate_max_propagation_depth(report),
            'critical_documents': self._identify_critical_documents(report)
        }
    
    def _calculate_max_propagation_depth(self, report: ConsistencyReport) -> int:
        """
        Calculate the maximum propagation depth in the impact analysis.
        
        Args:
            report: The consistency report
            
        Returns:
            The maximum propagation depth as an integer
        """
        # This is a placeholder for more complex graph analysis
        # In a real implementation, this would trace the dependency chain depth
        return min(3, len(report.metadata['impact']['propagation_paths']))
    
    def _identify_critical_documents(self, report: ConsistencyReport) -> List[str]:
        """
        Identify critical documents based on impact analysis.
        
        Args:
            report: The consistency report
            
        Returns:
            List of critical document paths
        """
        # Count how many times each document appears in propagation paths
        doc_counts = {}
        for path in report.metadata['impact']['propagation_paths']:
            doc = path['affected_document']
            doc_counts[doc] = doc_counts.get(doc, 0) + 1
        
        # Documents that appear in multiple paths are considered critical
        critical_docs = [doc for doc, count in doc_counts.items() if count > 1]
        return critical_docs[:5]  # Return top 5 critical documents
