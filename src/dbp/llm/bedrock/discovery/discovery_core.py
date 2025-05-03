###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Provides base discovery functionality shared between model and profile discovery.
# Centralizes common operations like region discovery and parallel scanning to avoid
# code duplication and ensure consistent behavior across discovery classes.
###############################################################################
# [Source file design principles]
# - Thread-safe operations for concurrent access
# - Efficient parallel scanning using ThreadPoolExecutor
# - Single responsibility for each class and function
# - Consistent error handling and logging
# - Clean separation from specific model/profile logic
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must avoid circular imports between discovery components
# - Must ensure consistent behavior across discovery types
# - Must be backward compatible with existing discovery usage
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# codebase:src/dbp/llm/bedrock/discovery/cache.py
# codebase:src/dbp/llm/bedrock/discovery/latency.py
# system:concurrent.futures
# system:threading
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-03T17:20:19Z : Initial implementation by CodeAssistant
# * Created BaseDiscovery class
# * Implemented parallel region scanning functionality
# * Added region discovery methods
###############################################################################

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Set, Callable, Tuple

# Local imports
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker

# External imports
from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError


class BaseDiscovery:
    """
    [Class intent]
    Base class for AWS Bedrock discovery operations, providing common functionality
    for both model and profile discovery to ensure consistent behavior and reduce
    code duplication.
    
    [Design principles]
    - Thread-safe operations for concurrent access
    - Efficient parallel region scanning
    - Consistent caching behavior
    - Standardized region management
    
    [Implementation details]
    - Uses AWSClientFactory for client access
    - Implements parallel region scanning with ThreadPoolExecutor
    - Provides common region discovery functionality
    - Handles region latency tracking
    """
    
    # Common constants
    INITIAL_BEDROCK_REGIONS = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", 
        "ap-southeast-1", "ap-southeast-2", "eu-central-1"
    ]
    
    def __init__(
        self,
        cache: Optional[DiscoveryCache] = None,
        client_factory: Optional[AWSClientFactory] = None,
        latency_tracker: Optional[RegionLatencyTracker] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the base discovery service with shared components.
        
        [Design principles]
        - Component dependency management
        - Consistent initialization across discovery types
        
        [Implementation details]
        - Sets up cache, client factory, and latency tracker
        - Creates components if not provided
        - Initializes logger
        
        Args:
            cache: Optional DiscoveryCache instance
            client_factory: Optional AWSClientFactory instance
            latency_tracker: Optional RegionLatencyTracker instance
            logger: Optional logger instance
        """
        self.cache = cache or DiscoveryCache()
        self.client_factory = client_factory or AWSClientFactory.get_instance()
        self.latency_tracker = latency_tracker or RegionLatencyTracker(cache=self.cache)
        self.logger = logger or logging.getLogger(__name__)
    
    def get_all_regions(self) -> List[str]:
        """
        [Method intent]
        Get list of all AWS regions where Bedrock might be available, combining
        known Bedrock regions with dynamically discovered AWS regions.
        
        [Design principles]
        - Dynamic discovery of available regions
        - Combination of static and dynamic information
        - Fallback to known regions on error
        
        [Implementation details]
        - Starts with initial known Bedrock regions
        - Uses EC2 client to discover all AWS regions
        - Returns combined unique list of regions to check
        - Handles discovery errors gracefully
        
        Returns:
            List of region names to check for Bedrock availability
        """
        regions_to_check = set(self.INITIAL_BEDROCK_REGIONS)
        
        try:
            # Get EC2 client to list all AWS regions
            ec2_client = self.client_factory.get_client('ec2', region_name='us-east-1')
            response = ec2_client.describe_regions()
            
            # Add all AWS regions to the list
            for region in response['Regions']:
                regions_to_check.add(region['RegionName'])
                
        except Exception as e:
            self.logger.warning(f"Failed to discover all AWS regions: {str(e)}")
            self.logger.warning("Using initial regions list only")
            
        return list(regions_to_check)

    def scan_regions_parallel(
        self, 
        regions: List[str],
        scan_function: Callable[[str], Any],
        max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Scan multiple AWS regions in parallel using a provided scan function, collecting
        and returning results in an efficient manner.
        
        [Design principles]
        - Parallel processing for efficiency
        - Generic implementation for reusability
        - Proper error handling
        
        [Implementation details]
        - Creates thread pool with appropriate size
        - Submits scan tasks for each region
        - Collects results as they complete
        - Handles errors in individual region scans
        - Returns mapping of regions to scan results
        
        Args:
            regions: List of regions to scan
            scan_function: Function to execute for each region (takes region string, returns any result)
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dict mapping regions to scan results
        """
        result = {}
        
        self.logger.info(f"Scanning {len(regions)} AWS regions in parallel...")
        
        # Use ThreadPoolExecutor to scan regions in parallel
        with ThreadPoolExecutor(max_workers=min(max_workers, len(regions))) as executor:
            # Submit scanning tasks
            future_to_region = {
                executor.submit(scan_function, region): region
                for region in regions
            }
            
            # Process results as they complete
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    scan_result = future.result()
                    if scan_result:
                        result[region] = scan_result
                except Exception as e:
                    self.logger.warning(f"Error scanning region {region}: {str(e)}")
        
        self.logger.info(f"Completed scanning {len(regions)} regions, found data in {len(result)} regions")
        return result
    
    def get_sorted_regions(self, regions: List[str]) -> List[str]:
        """
        [Method intent]
        Sort regions by measured latency to optimize region selection.
        
        [Design principles]
        - Latency-aware region selection
        - Consistent sorting behavior
        
        [Implementation details]
        - Uses latency tracker to sort regions
        - Returns regions sorted from lowest to highest latency
        
        Args:
            regions: List of AWS regions to sort
            
        Returns:
            List of region names sorted by latency (lowest first)
        """
        return self.latency_tracker.get_sorted_regions(regions)
    
    def is_valid_region(self, region: str) -> bool:
        """
        [Method intent]
        Check if a region name appears to be valid AWS region format.
        
        [Design principles]
        - Simple validation without API calls
        - Consistent region validation
        
        [Implementation details]
        - Basic format checking
        - Optional check against known regions
        
        Args:
            region: Region name to check
            
        Returns:
            Boolean indicating if region format appears valid
        """
        # Basic format check
        if not region or not isinstance(region, str):
            return False
        
        # Check format like "us-west-2"
        parts = region.split('-')
        if len(parts) < 2 or len(parts) > 3:
            return False
            
        # Additional check that second part is a direction
        directions = ["east", "west", "north", "south", "central", "northeast", "northwest", 
                     "southeast", "southwest"]
        if parts[1] not in directions:
            return False
            
        # If third part exists, it should be a number
        if len(parts) == 3:
            try:
                int(parts[2])
            except ValueError:
                return False
        
        return True
