from typing import List, Dict
from datetime import datetime

class EventManager:
    def __init__(self):
        self.events: List[Dict] = []
        self.frame_count = 0
        self.team_members = {}  # Track team members by robot_id

    def add_event(self, event_type: str, details: Dict) -> None:
        """Record a new event."""
        event = {
            'frame': self.frame_count,
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'details': details
        }
        self.events.append(event)

    def add_team_formation(self, robot_id: int, members: list) -> None:
        """Record a team formation event, avoiding duplicates."""
        # Get current member IDs for comparison
        new_member_ids = {id(m) for m in members}
        
        # Check if this is actually a new formation
        if robot_id in self.team_members:
            if self.team_members[robot_id] == new_member_ids:
                return  # Skip if same members
        
        # Record new team composition
        self.team_members[robot_id] = new_member_ids
        
        # Add the event
        self.add_event('team_formed', {
            'robot_id': robot_id,
            'leader': f"Robot-{robot_id%1000:03d}",
            'member_count': len(members),
            'member_types': [m.name for m in members]
        })

    def generate_story(self) -> str:
        """Generate narrative from recorded events."""
        if not self.events:
            return "No significant events occurred during this simulation run."

        story_parts = ["A new chapter unfolds in the simulation..."]
        
        # Process events chronologically
        sorted_events = sorted(self.events, key=lambda e: e['frame'])
        
        # Track formations and battles
        formations = []
        battles = []
        
        for event in sorted_events:
            if event['type'] == 'team_formed':
                details = event['details']
                formations.append(
                    f"Frame {event['frame']}: {details['leader']} formed a team with "
                    f"{details['member_count']} followers ({', '.join(details['member_types'])})"
                )
            elif event['type'] == 'battle':
                details = event['details']['result']
                battles.append(
                    f"Frame {event['frame']}: {details.get('outcome', 'unknown')} - "
                    f"{details.get('details', 'No details available')}"
                )

        # Add formations to story
        if formations:
            story_parts.append("\nTeams Formed:")
            story_parts.extend(formations)

        # Add battles to story
        if battles:
            story_parts.append("\nBattles Fought:")
            story_parts.extend(battles)

        # Add summary
        story_parts.append(f"\nTotal Events: {len(self.events)}")
        
        return "\n".join(story_parts)
