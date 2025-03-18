from typing import List, Dict
import re

class ActionParser:
    @staticmethod
    def parse_action_chain(content: str) -> Dict[str, List[Dict]]:
        action_chains = []
        special_actions = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Check if line starts with a number
            sequence_match = re.match(r'^(\d+)[.、]?\s*(.+)$', line)
            
            if sequence_match:
                sequence_num = int(sequence_match.group(1))
                actions_str = sequence_match.group(2)
                actions = [action.strip() for action in actions_str.split(',') if action.strip()]
                
                action_chains.append({
                    "sequence": sequence_num,
                    "actions": actions
                })
            else:
                # Handle special actions (lines without sequence numbers)
                actions = [action.strip() for action in line.split(',') if action.strip()]
                if actions:
                    special_actions.append({
                        "actions": actions
                    })
        
        # Sort action chains by sequence number
        action_chains.sort(key=lambda x: x["sequence"])
        
        return {
            "action_chains": action_chains,
            "special_actions": special_actions
        }