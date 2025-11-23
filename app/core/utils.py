from bson import ObjectId
from typing import Dict, Any


def build_id_query(id_value: str, field_name: str = "id") -> Dict[str, Any]:
    """
    Build a MongoDB query that works with both ObjectId and custom string IDs.
    
    Args:
        id_value: The ID value to search for
        field_name: The custom field name to fallback to (e.g., 'farm_id', 'slaughterhouse_id')
    
    Returns:
        A query dict that can be used with MongoDB find operations
    """
    if ObjectId.is_valid(id_value):
        try:
            return {"_id": ObjectId(id_value)}
        except:
            pass
    
    # If not a valid ObjectId, search by custom field
    return {f"{field_name}": id_value}
