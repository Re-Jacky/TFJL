from typing import Dict, List, Optional, Union
from app.enums.command_types import (
    CommandType, CardOperation, TimingPattern,
    FormationType, CardLevel, SpecialEventType
)

class CommandParser:
    def __init__(self, content: str):
        self.content = content
        self.result = {
            "formation": [],  # Initial formation
            "enhanced_cards": [],  # Enhanced/powered up cards
            "main_vehicle": None,  # Main vehicle
            "sub_vehicle": None,  # Sub vehicle
            "command_chain": [],  # Ordered list of commands
            "special_events": []  # Special event handlers
        }
    
    def parse_script(self) -> Dict[str, Union[List[Dict], List[str]]]:
        """Parse a script file into structured data."""
        lines = self.content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse formation line
            if line.startswith('上阵') and ('：' in line or ':' in line):
                formation_str = line[2:].replace('：', ':').split(':')[1].strip()
                self.result['formation'] = self._parse_formation(formation_str)
                continue
                
            # Parse enhanced cards
            if line.startswith('魔化') and ('：' in line or ':' in line):
                enhanced_str = line[2:].replace('：', ':').split(':')[1].strip()
                self.result['enhanced_cards'] = self._parse_enhanced_cards(enhanced_str)
                continue
                
            # Parse vehicles
            if line.startswith('主战车') and ('：' in line or ':' in line):
                self.result['main_vehicle'] = line.replace('：', ':').split(':')[1].strip()
                continue
            if line.startswith('副战车') and ('：' in line or ':' in line):
                self.result['sub_vehicle'] = line.replace('：', ':').split(':')[1].strip()
                continue
                
            # Parse command chains
            if line[0].isdigit():
                command = self._parse_command_chain(line)
                if command:
                    self.result['command_chain'].append(command)
            else:
                # Parse special events
                event = self._parse_special_event(line)
                if event:
                    self.result['special_events'].append(event)
                    
        return self.result
    
    def _parse_formation(self, formation_str: str) -> List[str]:
        """Parse initial formation string into list of cards."""
        return [card.strip() for card in formation_str.split(',') if card.strip()]
    
    def _parse_enhanced_cards(self, enhanced_str: str) -> List[str]:
        """Parse enhanced cards string into list of cards."""
        return [card.strip() for card in enhanced_str.split(',') if card.strip()]
    
    def _parse_command_chain(self, command_str: str) -> Optional[Dict]:
        """Parse a command chain string into structured data."""
        parts = command_str.split(',')
        if not parts:
            return None
            
        try:
            index = int(parts[0])
            commands = parts[1:]
            
            result = {
                "index": index,
                "commands": []
            }
            
            for cmd in commands:
                cmd = cmd.strip()
                if not cmd:
                    continue
                    
                # Parse timing patterns
                if any(pattern.value in cmd for pattern in TimingPattern):
                    timing = self._parse_timing(cmd)
                    if timing:
                        result['commands'].append(timing)
                        continue
                
                # Parse card operations
                if any(op.value in cmd for op in CardOperation):
                    operation = self._parse_card_operation(cmd)
                    if operation:
                        result['commands'].append(operation)
                        continue
                        
                # Parse formation types
                if any(form.value in cmd for form in FormationType):
                    formation = self._parse_formation_type(cmd)
                    if formation:
                        result['commands'].append(formation)

                # Parse special types
                if any(special.value in cmd for special in SpecialEventType):
                    special = self._parse_special_event(cmd)
                    if special:
                        result['commands'].append(special)
                        
            return result
        except ValueError:
            return None
    
    def _parse_timing(self, timing_str: str) -> Optional[Dict]:
        """Parse timing pattern string into structured data."""
        if TimingPattern.INTERVAL.value in timing_str:
            # Parse interval timing (每x秒共x次xxx)
            try:
                parts = timing_str.split('共')
                if len(parts) == 2:
                    interval = float(parts[0][1:-1])
                    count_parts = parts[1].split('次')
                    if len(count_parts) == 2:
                        count = int(count_parts[0])
                        card = count_parts[1]
                        return {
                            "type": CommandType.TIMING.value,
                            "pattern": TimingPattern.INTERVAL.value,
                            "interval": interval,
                            "count": count,
                            "target": card
                        }
            except (ValueError, IndexError):
                return None
        elif TimingPattern.FIXED.value in timing_str:
            # Parse fixed timing (时钟秒x)
            try:
                second = float(timing_str[3:])
                return {
                    "type": CommandType.TIMING.value,
                    "pattern": TimingPattern.FIXED.value,
                    "second": second
                }
            except (ValueError, IndexError):
                return None
        elif TimingPattern.DELAY.value in timing_str:
            # Parse delay timing (延时xxx)
            try:
                delay = float(timing_str[2:])
                return {
                    "type": CommandType.TIMING.value,
                    "pattern": TimingPattern.DELAY.value,
                    "delay": delay
                }
            except (ValueError, IndexError):
                return None
        elif TimingPattern.AFTER.value in timing_str:
            return {
                "type": CommandType.TIMING.value,
                "pattern": TimingPattern.AFTER.value,
            }
        return None
    
    def _parse_card_operation(self, operation_str: str) -> Optional[Dict]:
        """Parse card operation string into structured data."""
        for op in CardOperation:
            if op.value in operation_str:
                parts = operation_str.split(op.value)
                if len(parts) == 2:
                    card = parts[1]
                    level = None
                    
                    # Check for card level with priority for NOT_MAX
                    if CardLevel.NOT_MAX.value in card:
                        level = CardLevel.NOT_MAX.value
                        card = card.replace(CardLevel.NOT_MAX.value, '')
                    elif CardLevel.MAX.value in card:
                        level = CardLevel.MAX.value
                        card = card.replace(CardLevel.MAX.value, '')
                    elif CardLevel.SPECIFIC.value in card:
                        # Extract digit before SPECIFIC level
                        parts = card.split(CardLevel.SPECIFIC.value)
                        if parts[0] and parts[0][-1].isdigit():
                            level = parts[0][-1] + CardLevel.SPECIFIC.value
                            card = parts[0][:-1] + (parts[1] if len(parts) > 1 else '')
                        else:
                            level = CardLevel.SPECIFIC.value
                            card = card.replace(CardLevel.SPECIFIC.value, '')
                    
                    return {
                        "type": CommandType.CARD_OPERATION.value,
                        "operation": op.value,
                        "card": card,
                        "level": level
                    }
        return None
    
    def _parse_formation_type(self, formation_str: str)  -> Optional[Dict]:
        """Parse formation type string into structured data."""
        if FormationType.CANCEL_SAME_ROW.value in formation_str:
            return {
                "type": CommandType.FORMATION.value,
                "formation": FormationType.CANCEL_SAME_ROW.value,
                "card": None
            }
        if FormationType.SAME_ROW.value in formation_str:
            return {
                "type": CommandType.FORMATION.value,
                "formation": FormationType.SAME_ROW.value,
                "card": [formation_str.split(FormationType.SAME_ROW.value)[0]]
            }
        if FormationType.ORDERED.value in formation_str:
            return {
                "type": CommandType.FORMATION.value,
                "formation": FormationType.ORDERED.value,
            }
        return None
    
    def _parse_special_event(self, event_str: str) -> Optional[Dict]:
        """Parse special event string into structured data."""
        parts = event_str.split(',')
        if not parts:
            return None
            
        event_type = parts[0].strip()
        commands = []
        
        # Parse following commands
        for part in parts[1:]:
            part = part.strip()
                
            # Parse timing patterns
            if any(pattern.value in part for pattern in TimingPattern):
                timing = self._parse_timing(part)
                if timing:
                    commands.append(timing)
                    # continue
            
            # Parse card operations
            if any(op.value in part for op in CardOperation):
                operation = self._parse_card_operation(part)
                if operation:
                    commands.append(operation)

            # Parse special operations
                    
        return {
            "type": CommandType.SPECIAL_EVENT.value,
            "event": event_type,
            "commands": commands
        }