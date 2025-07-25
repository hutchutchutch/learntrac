"""
API for Learning Path plugin

Provides methods for other plugins to interact with learning paths.
"""

from trac.core import Component, ExtensionPoint, Interface
from trac.resource import Resource, ResourceNotFound
from trac.util.text import to_unicode


class ILearningPathProvider(Interface):
    """Extension point interface for components that provide learning paths."""
    
    def get_learning_paths(req):
        """Return an iterable of learning path names that this provider knows about.
        
        :param req: the request object
        :return: iterable of learning path names (strings)
        """
    
    def get_learning_path_info(req, name):
        """Return information about a specific learning path.
        
        :param req: the request object
        :param name: the learning path name
        :return: dict with learning path information or None if not found
        """
    
    def get_learning_resources(req, name):
        """Return resources associated with a learning path.
        
        :param req: the request object
        :param name: the learning path name
        :return: list of resource dicts
        """


class LearningPathSystem(Component):
    """System for managing learning paths."""
    
    learning_path_providers = ExtensionPoint(ILearningPathProvider)
    
    def get_all_learning_paths(self, req):
        """Get all learning paths from all providers."""
        paths = {}
        
        for provider in self.learning_path_providers:
            for name in provider.get_learning_paths(req):
                if name not in paths:
                    info = provider.get_learning_path_info(req, name)
                    if info:
                        paths[name] = info
        
        return paths
    
    def get_learning_path(self, req, name):
        """Get a specific learning path."""
        for provider in self.learning_path_providers:
            info = provider.get_learning_path_info(req, name)
            if info:
                return info
        
        return None
    
    def get_learning_path_tree(self, req, root_name=None, max_depth=3):
        """Build a tree structure of learning paths."""
        from .db import LearningPathDB
        
        db = LearningPathDB(self.env)
        
        def build_tree(parent_id, current_depth):
            if current_depth > max_depth:
                return []
            
            paths = db.get_learning_paths(parent_id=parent_id)
            tree = []
            
            for path in paths:
                # Get user progress if authenticated
                progress = None
                if req.authname and req.authname != 'anonymous':
                    progress = db.get_user_progress(req.authname, path['id'])
                
                node = {
                    'id': path['id'],
                    'name': path['name'],
                    'title': path['title'],
                    'description': path['description'],
                    'difficulty': path['difficulty'],
                    'estimated_hours': path['estimated_hours'],
                    'progress': progress,
                    'children': build_tree(path['id'], current_depth + 1),
                    'prerequisites': db.get_prerequisites(path['id']),
                    'resources': db.get_resources(path['id'])
                }
                tree.append(node)
            
            return tree
        
        if root_name:
            root = db.get_learning_path(name=root_name)
            if root:
                return build_tree(root['id'], 1)
            else:
                return []
        else:
            return build_tree(None, 1)
    
    def update_progress(self, req, path_name, progress=None, status=None):
        """Update user progress for a learning path."""
        if not req.authname or req.authname == 'anonymous':
            return False
        
        from .db import LearningPathDB
        db = LearningPathDB(self.env)
        
        path = db.get_learning_path(name=path_name)
        if not path:
            return False
        
        db.update_user_progress(
            req.authname, 
            path['id'], 
            progress=progress,
            status=status,
            completed=(progress == 100)
        )
        
        return True
    
    def get_user_paths(self, req, status_filter=None):
        """Get all learning paths for the current user."""
        if not req.authname or req.authname == 'anonymous':
            return []
        
        from .db import LearningPathDB
        db = LearningPathDB(self.env)
        
        progress_list = db.get_user_progress(req.authname)
        
        if status_filter:
            progress_list = [p for p in progress_list 
                           if p['status'] == status_filter]
        
        # Enrich with path information
        for progress in progress_list:
            path = db.get_learning_path(path_id=progress['path_id'])
            if path:
                progress['path'] = path
        
        return progress_list
    
    def recommend_next_path(self, req):
        """Recommend the next learning path for a user."""
        if not req.authname or req.authname == 'anonymous':
            return None
        
        from .db import LearningPathDB
        db = LearningPathDB(self.env)
        
        # Get user's completed paths
        completed = self.get_user_paths(req, status_filter='completed')
        completed_ids = {p['path_id'] for p in completed}
        
        # Get all paths
        all_paths = db.get_learning_paths()
        
        # Find paths where prerequisites are met
        recommendations = []
        
        for path in all_paths:
            if path['id'] in completed_ids:
                continue
            
            # Check prerequisites
            prereqs = db.get_prerequisites(path['id'])
            required_met = all(
                prereq['prerequisite_id'] in completed_ids 
                for prereq in prereqs 
                if prereq['required']
            )
            
            if required_met:
                # Calculate recommendation score
                score = 0
                
                # Higher score for paths with more completed prerequisites
                completed_prereqs = sum(
                    1 for prereq in prereqs 
                    if prereq['prerequisite_id'] in completed_ids
                )
                score += completed_prereqs * 10
                
                # Adjust for difficulty progression
                if path['difficulty'] == 'beginner':
                    score += 5
                elif path['difficulty'] == 'intermediate':
                    score += 3
                elif path['difficulty'] == 'advanced':
                    score += 1
                
                recommendations.append({
                    'path': path,
                    'score': score,
                    'prerequisites_met': completed_prereqs,
                    'total_prerequisites': len(prereqs)
                })
        
        # Sort by score and return top recommendation
        recommendations.sort(key=lambda r: r['score'], reverse=True)
        
        return recommendations[0] if recommendations else None