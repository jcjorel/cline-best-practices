# Bedrock Profile Algorithm Refactoring Plan

## Overview

This plan outlines how to refactor the profile-model mapping algorithm in the discovery module to match the approach used in `raw_api_profile_test.py`, focusing specifically on the algorithm that generates the region-based model structure with embedded profiles.

## Key Algorithm from raw_api_profile_test.py

The core algorithm in `raw_api_profile_test.py` that generates the all_regions_data structure works as follows:

1. Iterate through all AWS regions
2. For each region:
   - Fetch all models in the region 
   - Filter for project-supported models
   - Fetch all inference profiles in the region
   - Filter for profiles that reference project-supported models
   - Map profiles to models using ARN-based matching
   - Store the resulting models in a region-keyed dictionary

The most crucial part is how it builds the region-based model structure:

```python
# Store model data by region
all_regions_data = {}

# Process each AWS region
for region in all_regions:
    try:
        # Get all models in this region
        all_models = get_all_models(region)
        if not all_models:
            continue
            
        # Filter for project supported models
        filtered_models = filter_project_supported_items(all_models, "model")
        
        # Get all inference profiles in this region
        all_profiles = get_all_inference_profiles(region)
        
        # Filter for profiles that reference project supported models
        filtered_profiles = filter_project_supported_items(all_profiles, "profile")
        
        # Map profiles to models
        mapping = map_profiles_to_models(filtered_models, filtered_profiles)
        
        # Store this region's models in the result dictionary
        all_regions_data[region] = {model["modelId"]: model for model in filtered_models}
    except Exception as e:
        logger.error(f"Error processing region {region}: {str(e)}")

# Create final structure
merged_data = {
    "models": all_regions_data
}
```

## Implementation Plan for Discovery Module

### Phase 1: Update the Model-Profile Association Algorithm

1. Implement the ARN-based model-profile association in `BedrockProfileDiscovery`:
   
   ```python
   def associate_profiles_with_models(self, models, profiles):
       """
       Associate profiles with models using ARN-based extraction from profiles.
       """
       # Process each profile
       for profile in profiles:
           # Examine each model ARN in this profile
           for model_ref in profile.get("models", []):
               model_arn = model_ref.get("modelArn", "")
               if "/" in model_arn:
                   # Extract model ID from ARN
                   referenced_model_id = model_arn.split("/")[-1]
                   
                   # Find matching model
                   for model in models:
                       if model["modelId"] == referenced_model_id:
                           # Initialize referencedByInstanceProfiles if needed
                           if "referencedByInstanceProfiles" not in model:
                               model["referencedByInstanceProfiles"] = []
                           
                           # Avoid duplicates
                           profile_id = profile["inferenceProfileId"]
                           profile_already_added = any(
                               p["inferenceProfileId"] == profile_id
                               for p in model["referencedByInstanceProfiles"]
                           )
                           
                           if not profile_already_added:
                               # Add profile to model
                               model["referencedByInstanceProfiles"].append(profile)
                           
       return models
   ```

### Phase 2: Implement Region-Based Model Structure Builder

1. Add a method to build the complete region-based model structure:

   ```python
   def build_region_based_model_structure(self):
       """
       Build a region-based model structure with embedded profiles.
       """
       model_discovery = BedrockModelDiscovery.get_instance()
       all_regions_data = {}
       
       # Get all AWS regions
       regions = model_discovery._get_all_regions()
       
       # Process each region
       for region in regions:
           try:
               # Get models in this region
               models = model_discovery._scan_region(region)
               if not models:
                   continue
               
               # Get profiles in this region
               profiles = self.scan_profiles_in_region(region)
               
               # Associate profiles with models
               models = self.associate_profiles_with_models(models, profiles)
               
               # Store in region-based structure
               all_regions_data[region] = {model["modelId"]: model for model in models}
               
           except Exception as e:
               self.logger.warning(f"Error processing region {region}: {e}")
       
       return all_regions_data
   ```

### Phase 3: Update Cache Storage

1. Modify the cache storage to handle the new structure:

   ```python
   def store_model_profile_mapping(self, all_regions_data):
       """
       Store the region-based model-profile mapping in cache.
       """
       merged_data = {
           "models": all_regions_data
       }
       
       # Store in cache
       self.cache.set("bedrock_model_profile_mapping", merged_data)
       
       # Also update region-specific caches
       for region, models in all_regions_data.items():
           self.cache.set(f"bedrock_models:{region}", models)
   ```

### Phase 4: Create Public API Method

1. Add a public method to get the complete model-profile mapping:

   ```python
   def get_model_profile_mapping(self, refresh=False):
       """
       Get the complete model-profile mapping across regions.
       """
       # Try cache first
       if not refresh:
           cached_mapping = self.cache.get("bedrock_model_profile_mapping")
           if cached_mapping:
               return cached_mapping
       
       # Build from scratch
       all_regions_data = self.build_region_based_model_structure()
       
       # Cache results
       self.store_model_profile_mapping(all_regions_data)
       
       # Return the mapping
       return {
           "models": all_regions_data
       }
   ```

## Implementation Steps

1. Update `BedrockProfileDiscovery` with the ARN-based extraction and association
2. Implement the region-based model structure builder
3. Update cache handling for the new structure
4. Add the public API method for getting the mapping
5. Test the implementation against `raw_api_profile_test.py` output

## Testing Approach

1. Run the new implementation on the same AWS account as the raw_api_profile_test.py script 
2. Compare the structure and content of the model-profile mappings
3. Verify that all models requiring inference profiles have the correct associations
