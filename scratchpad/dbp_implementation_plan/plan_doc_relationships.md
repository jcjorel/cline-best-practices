# Documentation Relationships Implementation Plan

## Overview

This document outlines the implementation plan for the Documentation Relationships component, which is responsible for analyzing, tracking, and maintaining relationships between documentation files in the Documentation-Based Programming system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Documentation Structure and Relationships section
- [DOCUMENT_RELATIONSHIPS.md](../../doc/DOCUMENT_RELATIONSHIPS.md) - Documentation relationship specifications
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](../../doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - Data models

## Requirements

The Documentation Relationships component must:
1. Identify and track relationships between documentation files
2. Support different relationship types (e.g., depends on, impacts, references)
3. Maintain a directed graph of document relationships
4. Detect changes that affect related documentation
5. Provide interfaces to query relationships
6. Visualize relationships using Mermaid diagrams
7. Integrate with the database for persistent storage
8. Support document relationship metadata (e.g., relationship strength, scope)

## Design

### Documentation Relationships Architecture

The Documentation Relationships component follows a graph-based architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Relationship       │─────▶│  Relationship       │─────▶│  Relationship       │
│    Analyzer         │      │    Repository       │      │    Graph            │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Graph              │
                               ┌─────────────────────┐    │    Visualization    │
                               │                     │    │                     │
                               │  Impact             │    └─────────────────────┘
                               │    Analyzer         │               │
                               │                     │               │
                               └─────────────────────┘               ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Query              │
                               ┌─────────────────────┐    │    Interface        │
                               │                     │    │                     │
                               │  Change             │    └─────────────────────┘
                               │    Detector         │
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **DocRelationshipsComponent**

```python
class DocRelationshipsComponent(Component):
    """Component for managing documentation relationships."""
    
    @property
    def name(self) -> str:
        return "doc_relationships"
    
    @property
    def dependencies(self) -> list[str]:
        return ["database", "metadata_extraction"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the documentation relationships component."""
        self.config = context.config.doc_relationships
        self.logger = context.logger.get_child("doc_relationships")
        self.db_component = context.get_component("database")
        self.metadata_component = context.get_component("metadata_extraction")
        
        # Create relationship subcomponents
        self.relationship_repository = RelationshipRepository(self.db_component, self.logger)
        self.relationship_graph = RelationshipGraph(self.logger)
        self.relationship_analyzer = RelationshipAnalyzer(
            self.metadata_component, 
            self.relationship_repository,
            self.logger
        )
        self.impact_analyzer = ImpactAnalyzer(self.relationship_graph, self.logger)
        self.change_detector = ChangeDetector(self.impact_analyzer, self.logger)
        self.graph_visualization = GraphVisualization(self.relationship_graph, self.logger)
        self.query_interface = QueryInterface(self.relationship_graph, self.logger)
        
        # Load existing relationships
        self._load_relationships()
        
        self._initialized = True
    
    def _load_relationships(self) -> None:
        """Load existing relationships from the repository into the graph."""
        self.logger.info("Loading existing document relationships")
        
        # Get all relationships from the repository
        relationships = self.relationship_repository.get_all_relationships()
        
        # Add each relationship to the graph
        for relation in relationships:
            self.relationship_graph.add_relationship(
                source=relation.source_document,
                target=relation.target_document,
                relationship_type=relation.relationship_type,
                topic=relation.topic,
                scope=relation.scope,
                metadata=relation.metadata
            )
        
        self.logger.info(f"Loaded {len(relationships)} document relationships")
    
    def analyze_relationships(self, document_path: str) -> List[DocumentRelationship]:
        """
        Analyze relationships for a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            List of document relationships
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Analyzing relationships for document: {document_path}")
        
        # Analyze document relationships
        relationships = self.relationship_analyzer.analyze_document(document_path)
        
        # Update the repository and graph with new relationships
        self._update_relationships(document_path, relationships)
        
        return relationships
    
    def _update_relationships(self, document_path: str, relationships: List[DocumentRelationship]) -> None:
        """
        Update relationships for a document.
        
        Args:
            document_path: Path to the document
            relationships: List of document relationships
        """
        # Remove existing relationships for this document
        existing_relationships = self.relationship_repository.get_relationships_by_source(document_path)
        for relation in existing_relationships:
            self.relationship_repository.delete_relationship(relation.id)
            self.relationship_graph.remove_relationship(
                source=relation.source_document,
                target=relation.target_document,
                relationship_type=relation.relationship_type
            )
        
        # Add new relationships
        for relation in relationships:
            # Save to repository
            relation_id = self.relationship_repository.save_relationship(relation)
            relation.id = relation_id
            
            # Add to graph
            self.relationship_graph.add_relationship(
                source=relation.source_document,
                target=relation.target_document,
                relationship_type=relation.relationship_type,
                topic=relation.topic,
                scope=relation.scope,
                metadata=relation.metadata
            )
    
    def get_impacted_documents(self, document_path: str) -> List[DocImpact]:
        """
        Get documents impacted by changes to the specified document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            List of document impacts
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting impacted documents for: {document_path}")
        
        return self.impact_analyzer.analyze_impact(document_path)
    
    def detect_document_changes(self, document_path: str, old_content: str, new_content: str) -> List[DocChangeImpact]:
        """
        Detect changes in a document and their impact on related documents.
        
        Args:
            document_path: Path to the document
            old_content: Old document content
            new_content: New document content
            
        Returns:
            List of document change impacts
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Detecting changes in document: {document_path}")
        
        return self.change_detector.detect_changes(document_path, old_content, new_content)
    
    def get_related_documents(self, document_path: str, relationship_type: Optional[str] = None) -> List[DocumentRelationship]:
        """
        Get documents related to the specified document.
        
        Args:
            document_path: Path to the document
            relationship_type: Optional relationship type filter
            
        Returns:
            List of document relationships
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Getting related documents for: {document_path}")
        
        return self.query_interface.get_related_documents(document_path, relationship_type)
    
    def get_mermaid_diagram(self, document_paths: Optional[List[str]] = None) -> str:
        """
        Get a Mermaid diagram representing document relationships.
        
        Args:
            document_paths: Optional list of document paths to include in the diagram
            
        Returns:
            Mermaid diagram string
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info("Generating Mermaid diagram")
        
        return self.graph_visualization.generate_mermaid_diagram(document_paths)
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down document relationships component")
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **RelationshipRepository**

```python
class RelationshipRepository:
    """Repository for document relationships."""
    
    def __init__(self, db_component: Component, logger: Logger):
        self.db_component = db_component
        self.logger = logger
    
    def save_relationship(self, relationship: DocumentRelationship) -> str:
        """
        Save a document relationship.
        
        Args:
            relationship: Document relationship
            
        Returns:
            Relationship ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Convert relationship to ORM model
                relationship_orm = DocRelationshipORM(
                    source_document=relationship.source_document,
                    target_document=relationship.target_document,
                    relationship_type=relationship.relationship_type,
                    topic=relationship.topic,
                    scope=relationship.scope,
                    metadata=json.dumps(relationship.metadata) if relationship.metadata else None,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                session.add(relationship_orm)
                session.flush()
                
                relationship_id = str(relationship_orm.id)
                
                self.logger.debug(f"Saved relationship: {relationship_id}")
                
                return relationship_id
        
        except Exception as e:
            self.logger.error(f"Error saving relationship: {e}")
            raise RepositoryError(f"Error saving relationship: {e}")
    
    def update_relationship(self, relationship: DocumentRelationship) -> None:
        """
        Update a document relationship.
        
        Args:
            relationship: Document relationship
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get existing relationship
                relationship_orm = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.id == relationship.id
                ).first()
                
                if not relationship_orm:
                    raise RepositoryError(f"Relationship {relationship.id} not found")
                
                # Update fields
                relationship_orm.source_document = relationship.source_document
                relationship_orm.target_document = relationship.target_document
                relationship_orm.relationship_type = relationship.relationship_type
                relationship_orm.topic = relationship.topic
                relationship_orm.scope = relationship.scope
                relationship_orm.metadata = json.dumps(relationship.metadata) if relationship.metadata else None
                relationship_orm.updated_at = datetime.now()
                
                self.logger.debug(f"Updated relationship: {relationship.id}")
        
        except Exception as e:
            self.logger.error(f"Error updating relationship: {e}")
            raise RepositoryError(f"Error updating relationship: {e}")
    
    def delete_relationship(self, relationship_id: str) -> None:
        """
        Delete a document relationship.
        
        Args:
            relationship_id: Relationship ID
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Delete relationship
                result = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.id == relationship_id
                ).delete()
                
                if result == 0:
                    self.logger.warning(f"Relationship {relationship_id} not found for deletion")
                else:
                    self.logger.debug(f"Deleted relationship: {relationship_id}")
        
        except Exception as e:
            self.logger.error(f"Error deleting relationship: {e}")
            raise RepositoryError(f"Error deleting relationship: {e}")
    
    def get_relationship(self, relationship_id: str) -> Optional[DocumentRelationship]:
        """
        Get a document relationship by ID.
        
        Args:
            relationship_id: Relationship ID
            
        Returns:
            Document relationship or None if not found
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get relationship
                relationship_orm = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.id == relationship_id
                ).first()
                
                if not relationship_orm:
                    return None
                
                # Convert ORM model to relationship
                return self._convert_orm_to_relationship(relationship_orm)
        
        except Exception as e:
            self.logger.error(f"Error getting relationship {relationship_id}: {e}")
            raise RepositoryError(f"Error getting relationship: {e}")
    
    def get_all_relationships(self) -> List[DocumentRelationship]:
        """
        Get all document relationships.
        
        Returns:
            List of document relationships
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get all relationships
                relationship_orms = session.query(DocRelationshipORM).all()
                
                # Convert ORM models to relationships
                return [self._convert_orm_to_relationship(r) for r in relationship_orms]
        
        except Exception as e:
            self.logger.error(f"Error getting all relationships: {e}")
            raise RepositoryError(f"Error getting all relationships: {e}")
    
    def get_relationships_by_source(self, source_document: str) -> List[DocumentRelationship]:
        """
        Get document relationships by source document.
        
        Args:
            source_document: Source document path
            
        Returns:
            List of document relationships
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get relationships
                relationship_orms = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.source_document == source_document
                ).all()
                
                # Convert ORM models to relationships
                return [self._convert_orm_to_relationship(r) for r in relationship_orms]
        
        except Exception as e:
            self.logger.error(f"Error getting relationships for source {source_document}: {e}")
            raise RepositoryError(f"Error getting relationships: {e}")
    
    def get_relationships_by_target(self, target_document: str) -> List[DocumentRelationship]:
        """
        Get document relationships by target document.
        
        Args:
            target_document: Target document path
            
        Returns:
            List of document relationships
        """
        session = self.db_component.get_session()
        
        try:
            with session.begin():
                # Get relationships
                relationship_orms = session.query(DocRelationshipORM).filter(
                    DocRelationshipORM.target_document == target_document
                ).all()
                
                # Convert ORM models to relationships
                return [self._convert_orm_to_relationship(r) for r in relationship_orms]
        
        except Exception as e:
            self.logger.error(f"Error getting relationships for target {target_document}: {e}")
            raise RepositoryError(f"Error getting relationships: {e}")
    
    def _convert_orm_to_relationship(self, orm: DocRelationshipORM) -> DocumentRelationship:
        """Convert ORM model to document relationship."""
        return DocumentRelationship(
            id=str(orm.id),
            source_document=orm.source_document,
            target_document=orm.target_document,
            relationship_type=orm.relationship_type,
            topic=orm.topic,
            scope=orm.scope,
            metadata=json.loads(orm.metadata) if orm.metadata else {},
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )
```

3. **RelationshipGraph**

```python
class RelationshipGraph:
    """Graph representation of document relationships."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self.graph = networkx.MultiDiGraph()
    
    def add_relationship(self, source: str, target: str, relationship_type: str,
                        topic: Optional[str] = None, scope: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a relationship to the graph.
        
        Args:
            source: Source document
            target: Target document
            relationship_type: Relationship type
            topic: Optional topic
            scope: Optional scope
            metadata: Optional metadata
        """
        # Ensure nodes exist
        if source not in self.graph.nodes():
            self.graph.add_node(source, type="document", path=source)
        
        if target not in self.graph.nodes():
            self.graph.add_node(target, type="document", path=target)
        
        # Add edge
        self.graph.add_edge(
            source, 
            target, 
            relationship_type=relationship_type,
            topic=topic,
            scope=scope,
            metadata=metadata or {}
        )
        
        self.logger.debug(f"Added relationship: {source} -{relationship_type}-> {target}")
    
    def remove_relationship(self, source: str, target: str, relationship_type: Optional[str] = None) -> None:
        """
        Remove a relationship from the graph.
        
        Args:
            source: Source document
            target: Target document
            relationship_type: Optional relationship type
        """
        # Find edges between source and target
        edges_to_remove = []
        
        for _, _, key, data in self.graph.edges(keys=True, data=True):
            if _ == source and target == target:
                if relationship_type is None or data.get("relationship_type") == relationship_type:
                    edges_to_remove.append((source, target, key))
        
        # Remove edges
        for edge in edges_to_remove:
            self.graph.remove_edge(*edge)
            
            self.logger.debug(f"Removed relationship: {source} -> {target}")
        
        # Remove isolated nodes
        for node in list(self.graph.nodes()):
            if self.graph.degree(node) == 0:
                self.graph.remove_node(node)
    
    def get_outgoing_relationships(self, source: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Get outgoing relationships from a document.
        
        Args:
            source: Source document
            
        Returns:
            List of (target, relationship_type, attributes) tuples
        """
        if source not in self.graph.nodes():
            return []
        
        relationships = []
        
        for _, target, data in self.graph.out_edges(source, data=True):
            relationships.append((target, data.get("relationship_type"), data))
        
        return relationships
    
    def get_incoming_relationships(self, target: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Get incoming relationships to a document.
        
        Args:
            target: Target document
            
        Returns:
            List of (source, relationship_type, attributes) tuples
        """
        if target not in self.graph.nodes():
            return []
        
        relationships = []
        
        for source, _, data in self.graph.in_edges(target, data=True):
            relationships.append((source, data.get("relationship_type"), data))
        
        return relationships
    
    def get_all_relationships(self) -> List[Tuple[str, str, str, Dict[str, Any]]]:
        """
        Get all relationships in the graph.
        
        Returns:
            List of (source, target, relationship_type, attributes) tuples
        """
        relationships = []
        
        for source, target, data in self.graph.edges(data=True):
            relationships.append((source, target, data.get("relationship_type"), data))
        
        return relationships
    
    def get_subgraph(self, nodes: List[str]) -> "RelationshipGraph":
        """
        Get a subgraph containing only the specified nodes.
        
        Args:
            nodes: List of node IDs
            
        Returns:
            Subgraph as a new RelationshipGraph
        """
        # Create a new graph
        subgraph = RelationshipGraph(self.logger)
        
        # Get the NetworkX subgraph
        nodes_in_graph = [node for node in nodes if node in self.graph.nodes()]
        nx_subgraph = self.graph.subgraph(nodes_in_graph)
        
        # Copy edges and attributes to the new graph
        for source, target, data in nx_subgraph.edges(data=True):
            subgraph.add_relationship(
                source=source,
                target=target,
                relationship_type=data.get("relationship_type"),
                topic=data.get("topic"),
                scope=data.get("scope"),
                metadata=data.get("metadata")
            )
        
        return subgraph
    
    def find_paths(self, source: str, target: str, max_length: int = 5) -> List[List[Tuple[str, str, str]]]:
        """
        Find paths between two documents.
        
        Args:
            source: Source document
            target: Target document
            max_length: Maximum path length
            
        Returns:
            List of paths, where each path is a list of (node, relationship_type, node) tuples
        """
        if source not in self.graph.nodes() or target not in self.graph.nodes():
            return []
        
        try:
            # Find all simple paths
            simple_paths = list(networkx.all_simple_paths(
                self.graph, source, target, cutoff=max_length
            ))
            
            # Convert to format with relationship types
            result = []
            
            for path in simple_paths:
                formatted_path = []
                
                for i in range(len(path) - 1):
                    node1 = path[i]
                    node2 = path[i+1]
                    
                    # Get edge data (there may be multiple edges)
                    edge_data = self.graph.get_edge_data(node1, node2)
                    
                    # Use the first edge (we could return all, but that's more complex)
                    first_edge_key = list(edge_data.keys())[0]
                    relationship_type = edge_data[first_edge_key].get("relationship_type")
                    
                    formatted_path.append((node1, relationship_type, node2))
                
                result.append(formatted_path)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error finding paths from {source} to {target}: {e}")
            return []
```

4. **RelationshipAnalyzer**

```python
class RelationshipAnalyzer:
    """Analyzes document relationships."""
    
    def __init__(self, metadata_component: Component, repository: RelationshipRepository, logger: Logger):
        self.metadata_component = metadata_component
        self.repository = repository
        self.logger = logger
    
    def analyze_document(self, document_path: str) -> List[DocumentRelationship]:
        """
        Analyze relationships for a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            List of document relationships
        """
        self.logger.info(f"Analyzing relationships for document: {document_path}")
        
        # Get document content
        try:
            with open(document_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Error reading document {document_path}: {e}")
            return []
        
        # First check if this is a DOCUMENT_RELATIONSHIPS.md file
        if os.path.basename(document_path) == "DOCUMENT_RELATIONSHIPS.md":
            return self._analyze_relationships_document(document_path, content)
        
        # Otherwise analyze normal markdown document
        return self._analyze_markdown_document(document_path, content)
    
    def _analyze_relationships_document(self, document_path: str, content: str) -> List[DocumentRelationship]:
        """Analyze a DOCUMENT_RELATIONSHIPS.md file."""
        relationships = []
        
        # Extract document declarations from content using regex patterns
        # Format example:
        # ## [Primary Document]
        # - Depends on: [Related Document 1] - Topic: [subject matter] - Scope: [narrow/broad/specific area]
        # - Impacts: [Related Document 2] - Topic: [subject matter] - Scope: [narrow/broad/specific area]
        
        # Pattern for document section headers
        section_pattern = r"##\s+\[(.*?)\]"
        sections = re.finditer(section_pattern, content)
        
        for section_match in sections:
            source_document = section_match.group(1).strip()
            source_start = section_match.end()
            
            # Find the end of this section (next section or end of file)
            next_section = re.search(section_pattern, content[source_start:])
            section_end = source_start + next_section.start() if next_section else len(content)
            section_content = content[source_start:section_end]
            
            # Pattern for relationship lines
            rel_pattern = r"-\s+(.*?):\s+\[(.*?)\](?:\s+-\s+Topic:\s+\[(.*?)\])?(?:\s+-\s+Scope:\s+\[(.*?)\])?"
            relationship_matches = re.finditer(rel_pattern, section_content)
            
            for rel_match in relationship_matches:
                relationship_type = rel_match.group(1).strip()
                target_document = rel_match.group(2).strip()
                topic = rel_match.group(3).strip() if rel_match.group(3) else None
                scope = rel_match.group(4).strip() if rel_match.group(4) else None
                
                # Create relationship
                relationship = DocumentRelationship(
                    id=None,  # Will be assigned when saved
                    source_document=source_document,
                    target_document=target_document,
                    relationship_type=relationship_type,
                    topic=topic,
                    scope=scope,
                    metadata={},
                    created_at=None,  # Will be set when saved
                    updated_at=None   # Will be set when saved
                )
                
                relationships.append(relationship)
        
        self.logger.info(f"Found {len(relationships)} relationships in {document_path}")
        return relationships
    
    def _analyze_markdown_document(self, document_path: str, content: str) -> List[DocumentRelationship]:
        """Analyze a regular markdown document."""
        relationships = []
        
        # Extract links from markdown content
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.finditer(link_pattern, content)
        
        for link_match in links:
            link_text = link_match.group(1).strip()
            link_target = link_match.group(2).strip()
            
            # Only process internal document links
            if not link_target.startswith("http") and not link_target.startswith("#"):
                # Normalize the path
                target_document = os.path.normpath(
                    os.path.join(os.path.dirname(document_path), link_target)
                )
                
                # Create relationship
                relationship = DocumentRelationship(
                    id=None,  # Will be assigned when saved
                    source_document=document_path,
                    target_document=target_document,
                    relationship_type="references",
                    topic=link_text,
                    scope="narrow",
                    metadata={},
                    created_at=None,  # Will be set when saved
                    updated_at=None   # Will be set when saved
                )
                
                relationships.append(relationship)
        
        # Check for special sections like "Depends on" or "Impacts"
        section_patterns = {
            "depends on": r"(?:^|\n)#+\s*Depends\s+on\s*\n(.*?)(?:\n#+|$)",
            "impacts": r"(?:^|\n)#+\s*Impacts\s*\n(.*?)(?:\n#+|$)",
            "related to": r"(?:^|\n)#+\s*Related\s+(?:to|documents)\s*\n(.*?)(?:\n#+|$)"
        }
        
        for rel_type, pattern in section_patterns.items():
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                section_content = match.group(1).strip()
                
                # Extract items from section (assuming list format)
                item_pattern = r"[-*]\s+(.*?)(?:\n|$)"
                items = re.finditer(item_pattern, section_content)
                
                for item_match in items:
                    item_text = item_match.group(1).strip()
                    
                    # Check if item contains a link
                    link_match = re.search(link_pattern, item_text)
                    
                    if link_match:
                        link_text = link_match.group(1).strip()
                        link_target = link_match.group(2).strip()
                        
                        # Normalize the path
                        target_document = os.path.normpath(
                            os.path.join(os.path.dirname(document_path), link_target)
                        )
                        
                        # Extract topic and scope if present
                        topic_match = re.search(r"Topic:\s+(.+?)(?:\s+-|$)", item_text)
                        scope_match = re.search(r"Scope:\s+(.+?)(?:\s+-|$)", item_text)
                        
                        topic = topic_match.group(1).strip() if topic_match else link_text
                        scope = scope_match.group(1).strip() if scope_match else "narrow"
                        
                        # Create relationship
                        relationship = DocumentRelationship(
                            id=None,  # Will be assigned when saved
                            source_document=document_path,
                            target_document=target_document,
                            relationship_type=rel_type,
                            topic=topic,
                            scope=scope,
                            metadata={},
                            created_at=None,  # Will be set when saved
                            updated_at=None   # Will be set when saved
                        )
                        
                        relationships.append(relationship)
        
        self.logger.info(f"Found {len(relationships)} relationships in {document_path}")
        return relationships
```

5. **ImpactAnalyzer**

```python
class ImpactAnalyzer:
    """Analyzes impact of document changes."""
    
    def __init__(self, relationship_graph: RelationshipGraph, logger: Logger):
        self.relationship_graph = relationship_graph
        self.logger = logger
    
    def analyze_impact(self, document_path: str) -> List[DocImpact]:
        """
        Analyze impact of changes to a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            List of document impacts
        """
        self.logger.info(f"Analyzing impact of changes to {document_path}")
        
        impacts = []
        
        # Get outgoing relationships ("impacts", "depends on", etc.)
        outgoing_relationships = self.relationship_graph.get_outgoing_relationships(document_path)
        
        for target, relationship_type, attributes in outgoing_relationships:
            # Documents directly impacted by the source document
            if relationship_type == "impacts":
                impact = DocImpact(
                    source_document=document_path,
                    target_document=target,
                    impact_type="direct",
                    impact_level="high",
                    relationship_type=relationship_type,
                    topic=attributes.get("topic"),
                    scope=attributes.get("scope")
                )
                impacts.append(impact)
        
        # Get incoming relationships (documents that depend on this one)
        incoming_relationships = self.relationship_graph.get_incoming_relationships(document_path)
        
        for source, relationship_type, attributes in incoming_relationships:
            # Documents that depend on the changed document
            if relationship_type == "depends on":
                impact = DocImpact(
                    source_document=document_path,
                    target_document=source,
                    impact_type="reverse",
                    impact_level="high",
                    relationship_type=relationship_type,
                    topic=attributes.get("topic"),
                    scope=attributes.get("scope")
                )
                impacts.append(impact)
        
        # Find indirect impacts (transitive relationships)
        # For each document that directly depends on the changed document,
        # find documents that depend on those
        for source, relationship_type, _ in incoming_relationships:
            if relationship_type == "depends on":
                secondary_incoming = self.relationship_graph.get_incoming_relationships(source)
                
                for tertiary_source, tertiary_rel_type, tertiary_attributes in secondary_incoming:
                    if tertiary_rel_type == "depends on":
                        impact = DocImpact(
                            source_document=document_path,
                            target_document=tertiary_source,
                            impact_type="indirect",
                            impact_level="medium",
                            relationship_type="transitive",
                            topic=tertiary_attributes.get("topic"),
                            scope=tertiary_attributes.get("scope")
                        )
                        impacts.append(impact)
        
        self.logger.info(f"Found {len(impacts)} impacted documents for {document_path}")
        return impacts
```

6. **ChangeDetector**

```python
class ChangeDetector:
    """Detects changes in documents."""
    
    def __init__(self, impact_analyzer: ImpactAnalyzer, logger: Logger):
        self.impact_analyzer = impact_analyzer
        self.logger = logger
    
    def detect_changes(self, document_path: str, old_content: str, new_content: str) -> List[DocChangeImpact]:
        """
        Detect changes in a document and their impact on related documents.
        
        Args:
            document_path: Path to the document
            old_content: Old document content
            new_content: New document content
            
        Returns:
            List of document change impacts
        """
        self.logger.info(f"Detecting changes in {document_path}")
        
        # Detect changes between old and new content
        changes = self._detect_content_changes(old_content, new_content)
        
        if not changes:
            self.logger.info(f"No significant changes detected in {document_path}")
            return []
        
        # Analyze impact of changes
        impacts = self.impact_analyzer.analyze_impact(document_path)
        
        # Combine changes and impacts
        change_impacts = []
        
        for change in changes:
            for impact in impacts:
                # Create a DocChangeImpact for each combination of change and impact
                change_impact = DocChangeImpact(
                    source_document=document_path,
                    target_document=impact.target_document,
                    change_type=change["type"],
                    change_section=change["section"],
                    change_content=change["content"],
                    impact_type=impact.impact_type,
                    impact_level=impact.impact_level,
                    relationship_type=impact.relationship_type,
                    topic=impact.topic,
                    scope=impact.scope
                )
                
                change_impacts.append(change_impact)
        
        self.logger.info(f"Found {len(change_impacts)} change impacts for {document_path}")
        return change_impacts
    
    def _detect_content_changes(self, old_content: str, new_content: str) -> List[Dict[str, str]]:
        """
        Detect changes between old and new document content.
        
        Args:
            old_content: Old document content
            new_content: New document content
            
        Returns:
            List of changes, each with type, section, and content
        """
        changes = []
        
        # Split content into sections based on headers
        old_sections = self._split_into_sections(old_content)
        new_sections = self._split_into_sections(new_content)
        
        # Find added sections
        for section_title, section_content in new_sections.items():
            if section_title not in old_sections:
                changes.append({
                    "type": "section_added",
                    "section": section_title,
                    "content": section_content[:100] + "..." if len(section_content) > 100 else section_content
                })
        
        # Find removed sections
        for section_title, section_content in old_sections.items():
            if section_title not in new_sections:
                changes.append({
                    "type": "section_removed",
                    "section": section_title,
                    "content": section_content[:100] + "..." if len(section_content) > 100 else section_content
                })
        
        # Find modified sections
        for section_title in set(old_sections.keys()) & set(new_sections.keys()):
            old_section = old_sections[section_title]
            new_section = new_sections[section_title]
            
            if old_section != new_section:
                changes.append({
                    "type": "section_modified",
                    "section": section_title,
                    "content": f"Changed from {len(old_section)} to {len(new_section)} characters"
                })
        
        return changes
    
    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """
        Split document content into sections based on headers.
        
        Args:
            content: Document content
            
        Returns:
            Dictionary mapping section titles to section content
        """
        sections = {}
        current_section = "preamble"
        current_content = []
        
        # Split content into lines
        lines = content.split("\n")
        
        for line in lines:
            # Check if line is a header
            if line.startswith("#"):
                # Save previous section
                sections[current_section] = "\n".join(current_content)
                current_content = []
                
                # Extract section title
                header_match = re.match(r"#+\s+(.*)", line)
                if header_match:
                    current_section = header_match.group(1).strip()
                else:
                    current_section = line
            
            current_content.append(line)
        
        # Save last section
        sections[current_section] = "\n".join(current_content)
        
        return sections
```

7. **GraphVisualization**

```python
class GraphVisualization:
    """Visualization of document relationships."""
    
    def __init__(self, relationship_graph: RelationshipGraph, logger: Logger):
        self.relationship_graph = relationship_graph
        self.logger = logger
    
    def generate_mermaid_diagram(self, document_paths: Optional[List[str]] = None) -> str:
        """
        Generate a Mermaid diagram for document relationships.
        
        Args:
            document_paths: Optional list of document paths to include in the diagram
            
        Returns:
            Mermaid diagram string
        """
        self.logger.info("Generating Mermaid diagram")
        
        # Get subgraph if document_paths provided, otherwise use full graph
        graph = self.relationship_graph
        if document_paths:
            graph = self.relationship_graph.get_subgraph(document_paths)
        
        # Start Mermaid diagram
        mermaid = ["```mermaid", "graph TD;"]
        
        # Define node styles
        mermaid.append("classDef coreDoc fill:#f9f,stroke:#333,stroke-width:2px;")
        mermaid.append("classDef supportDoc fill:#bbf,stroke:#333,stroke-width:1px;")
        
        # Add nodes
        nodes = {}
        
        for source, target, rel_type, attrs in graph.get_all_relationships():
            # Generate node IDs
            source_id = self._safe_node_id(source)
            target_id = self._safe_node_id(target)
            
            # Add nodes if new
            if source not in nodes:
                source_label = os.path.basename(source)
                mermaid.append(f"{source_id}[\"{source_label}\"]")
                nodes[source] = True
            
            if target not in nodes:
                target_label = os.path.basename(target)
                mermaid.append(f"{target_id}[\"{target_label}\"]")
                nodes[target] = True
            
            # Add edge
            edge_label = rel_type.replace(" ", "_")
            mermaid.append(f"{source_id} -->|{edge_label}| {target_id}")
        
        # Add class assignments for core documents
        core_docs = ["DESIGN.md", "DATA_MODEL.md", "CONFIGURATION.md", "API.md", "SECURITY.md"]
        for node in nodes:
            node_id = self._safe_node_id(node)
            node_name = os.path.basename(node)
            
            if node_name in core_docs:
                mermaid.append(f"class {node_id} coreDoc;")
            else:
                mermaid.append(f"class {node_id} supportDoc;")
        
        # End Mermaid diagram
        mermaid.append("```")
        
        return "\n".join(mermaid)
    
    def _safe_node_id(self, node_path: str) -> str:
        """
        Generate a safe node ID for Mermaid diagram.
        
        Args:
            node_path: Document path
            
        Returns:
            Safe node ID
        """
        # Strip path
        node_name = os.path.basename(node_path)
        
        # Remove extension
        node_name = os.path.splitext(node_name)[0]
        
        # Replace spaces with underscores
        node_name = node_name.replace(" ", "_")
        
        # Remove special characters
        node_name = re.sub(r"[^a-zA-Z0-9_]", "", node_name)
        
        # Ensure it starts with a letter
        if not node_name[0].isalpha():
            node_name = "doc_" + node_name
        
        return node_name
```

8. **QueryInterface**

```python
class QueryInterface:
    """Interface for querying document relationships."""
    
    def __init__(self, relationship_graph: RelationshipGraph, logger: Logger):
        self.relationship_graph = relationship_graph
        self.logger = logger
    
    def get_related_documents(self, document_path: str, relationship_type: Optional[str] = None) -> List[DocumentRelationship]:
        """
        Get documents related to the specified document.
        
        Args:
            document_path: Path to the document
            relationship_type: Optional relationship type filter
            
        Returns:
            List of document relationships
        """
        self.logger.info(f"Getting related documents for {document_path}")
        
        relationships = []
        
        # Get outgoing relationships
        outgoing = self.relationship_graph.get_outgoing_relationships(document_path)
        
        for target, rel_type, attrs in outgoing:
            if relationship_type is None or rel_type == relationship_type:
                relationship = DocumentRelationship(
                    id=None,  # No ID for synthetic relationships
                    source_document=document_path,
                    target_document=target,
                    relationship_type=rel_type,
                    topic=attrs.get("topic"),
                    scope=attrs.get("scope"),
                    metadata=attrs.get("metadata", {}),
                    created_at=None,
                    updated_at=None
                )
                relationships.append(relationship)
        
        # Get incoming relationships
        incoming = self.relationship_graph.get_incoming_relationships(document_path)
        
        for source, rel_type, attrs in incoming:
            if relationship_type is None or rel_type == relationship_type:
                relationship = DocumentRelationship(
                    id=None,  # No ID for synthetic relationships
                    source_document=source,
                    target_document=document_path,
                    relationship_type=rel_type,
                    topic=attrs.get("topic"),
                    scope=attrs.get("scope"),
                    metadata=attrs.get("metadata", {}),
                    created_at=None,
                    updated_at=None
                )
                relationships.append(relationship)
        
        self.logger.info(f"Found {len(relationships)} related documents for {document_path}")
        return relationships
    
    def get_dependency_chain(self, document_path: str, max_depth: int = 3) -> List[List[DocumentRelationship]]:
        """
        Get dependency chains starting from the specified document.
        
        Args:
            document_path: Path to the document
            max_depth: Maximum chain depth
            
        Returns:
            List of dependency chains, where each chain is a list of document relationships
        """
        self.logger.info(f"Getting dependency chain for {document_path}")
        
        chains = []
        
        # Find all outgoing dependencies
        dependencies = [
            target for target, rel_type, _ in 
            self.relationship_graph.get_outgoing_relationships(document_path)
            if rel_type == "depends on"
        ]
        
        for dep in dependencies:
            # Find paths to this dependency
            paths = self.relationship_graph.find_paths(document_path, dep, max_length=max_depth)
            
            # Convert paths to chains of relationships
            for path in paths:
                chain = []
                
                for source, rel_type, target in path:
                    # Get edge attributes
                    attrs = {}
                    for _, _, edge_attrs in self.relationship_graph.get_outgoing_relationships(source):
                        if _ == target:
                            attrs = edge_attrs
                            break
                    
                    relationship = DocumentRelationship(
                        id=None,  # No ID for synthetic relationships
                        source_document=source,
                        target_document=target,
                        relationship_type=rel_type,
                        topic=attrs.get("topic"),
                        scope=attrs.get("scope"),
                        metadata=attrs.get("metadata", {}),
                        created_at=None,
                        updated_at=None
                    )
                    
                    chain.append(relationship)
                
                chains.append(chain)
        
        self.logger.info(f"Found {len(chains)} dependency chains for {document_path}")
        return chains
```

### Data Model Classes

1. **DocumentRelationship**

```python
@dataclass
class DocumentRelationship:
    """Document relationship model."""
    
    source_document: str
    target_document: str
    relationship_type: str  # e.g., "depends on", "impacts", "references"
    topic: Optional[str]
    scope: Optional[str]  # e.g., "narrow", "broad", "specific area"
    metadata: Dict[str, Any]
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

2. **DocImpact**

```python
@dataclass
class DocImpact:
    """Document impact model."""
    
    source_document: str
    target_document: str
    impact_type: str  # e.g., "direct", "reverse", "indirect"
    impact_level: str  # e.g., "high", "medium", "low"
    relationship_type: str
    topic: Optional[str] = None
    scope: Optional[str] = None
```

3. **DocChangeImpact**

```python
@dataclass
class DocChangeImpact:
    """Document change impact model."""
    
    source_document: str
    target_document: str
    change_type: str  # e.g., "section_added", "section_removed", "section_modified"
    change_section: str
    change_content: str
    impact_type: str
    impact_level: str
    relationship_type: str
    topic: Optional[str] = None
    scope: Optional[str] = None
```

4. **DocRelationshipORM**

```python
class DocRelationshipORM(Base):
    """ORM model for document relationships."""
    
    __tablename__ = "doc_relationships"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_document = Column(String, nullable=False)
    target_document = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

### Configuration Class

```python
@dataclass
class DocRelationshipsConfig:
    """Configuration for document relationships."""
    
    relationship_types: List[str]
    core_documents: List[str]
    supported_scopes: List[str]
    mermaid_diagram_node_limit: int
    path_search_limit: int
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `relationship_types` | Supported relationship types | `["depends on", "impacts", "references", "related to"]` | List of valid relationship types |
| `core_documents` | List of core documentation files | `["DESIGN.md", "DATA_MODEL.md", "API.md", "SECURITY.md", "CONFIGURATION.md"]` | List of document paths |
| `supported_scopes` | Supported scope values | `["narrow", "broad", "specific area"]` | List of valid scope values |
| `mermaid_diagram_node_limit` | Maximum nodes in Mermaid diagram | `20` | `5-100` |
| `path_search_limit` | Maximum path length for searches | `5` | `1-10` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement DocRelationshipsComponent as a system component
2. Define data model classes (DocumentRelationship, DocImpact, DocChangeImpact)
3. Create configuration class and default values
4. Implement ORM model for document relationships

### Phase 2: Graph Implementation
1. Implement RelationshipGraph using NetworkX
2. Create RelationshipRepository for persistent storage
3. Implement RelationshipAnalyzer for extracting relationships from documents
4. Implement advanced graph algorithms for relationship analysis

### Phase 3: Analysis and Visualization
1. Implement ImpactAnalyzer for determining document impact
2. Create ChangeDetector for detecting document changes
3. Implement GraphVisualization for generating Mermaid diagrams
4. Create QueryInterface for relationship queries

### Phase 4: Integration
1. Integrate with metadata extraction component
2. Connect to the database component
3. Set up event handlers for document changes
4. Implement automatic relationship extraction on document changes

## Security Considerations

The Documentation Relationships component implements these security measures:
- Validation of document paths to prevent path traversal attacks
- Sanitization of user-provided relationship metadata
- Safe handling of markdown content during relationship extraction
- Proper error isolation and reporting
- Thread safety for concurrent access to the relationship graph
- Protection against cycles in the relationship graph
- Proper handling of file I/O operations

## Testing Strategy

### Unit Tests
- Test graph operations for correctness
- Test relationship extraction with various markdown formats
- Test Mermaid diagram generation
- Test change detection algorithms

### Integration Tests
- Test database persistence of relationships
- Test integration with document change events
- Test impact analysis with complex relationship graphs

### System Tests
- Test performance with large document sets
- Test visualization of complex document relationships
- Test concurrent access to the relationship graph

## Dependencies on Other Plans

This plan depends on:
- Database Schema plan (for ORM models)
- Metadata Extraction plan (for document analysis)
- Component Initialization plan (for component framework)

## Implementation Timeline

1. Core Structure - 2 days
2. Graph Implementation - 2 days
3. Analysis and Visualization - 3 days
4. Integration - 1 day

Total: 8 days
