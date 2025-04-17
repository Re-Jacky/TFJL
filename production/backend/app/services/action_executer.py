from app.services.game_service import GameService
from app.enums.command_types import CommandType, FormationType

class ActionExecuter:
    def __init__(self, pid):
        self.pid = pid

    def execute(self, actions):
        """
        actions: List[Dict]，可以是解析器输出的动作列表，也可以是 sample.json 中的 command_chain
        """
        # 如果 actions 是 command_chain 结构，则遍历每个根动作
        if isinstance(actions, dict) and "command_chain" in actions:
            command_chains = actions["command_chain"]
        else:
            command_chains = actions
        for chain in command_chains:
            summary = self.summarize_chain(chain)
            print(f"执行命令链 index={chain.get('index', '?')}，摘要: {summary}")
            commands = chain.get("commands", [])
            # 新增：先收集formation和card_op，最后统一部署
            formation_info = None
            card_ops = []
            special_cards = []
            for cmd in commands:
                if cmd.get("type") == CommandType.FORMATION.value:
                    formation_info = cmd
                elif cmd.get("type") == CommandType.CARD_OPERATION.value:
                    card_ops.append(cmd)
                elif cmd.get("type") == CommandType.SPECIAL_EVENT.value:
                    special_cards.append(cmd)
                else:
                    self.dispatch_command(cmd)
            # 处理编队和卡牌部署
            layout, special = self.handle_formation(formation_info, card_ops) if formation_info else (None, {})
            if layout is None:
                layout, special = self.handle_card_operation(None, card_ops)
            # 处理特殊卡牌如宝库
            for sc in special_cards:
                if sc.get("card") == "宝库":
                    special["top"] = "宝库"
            # 部署卡牌
            self.deploy_cards({"layout": layout, "special": special})

    def summarize_chain(self, chain):
        """
        对每个命令链进行归纳，返回主要操作类型摘要
        """
        commands = chain.get("commands", [])
        types = set()
        for cmd in commands:
            t = cmd.get("type")
            if t == CommandType.CARD_OPERATION.value:
                types.add("卡牌操作")
            elif t == CommandType.FORMATION.value:
                types.add("编队")
            elif t == CommandType.SPECIAL_EVENT.value:
                types.add("特殊事件")
            elif t == CommandType.TIMING.value:
                types.add("时序")
            else:
                types.add(t)
        return ",".join(types)

    def dispatch_command(self, cmd):
        """
        根据命令类型分发到对应处理方法
        """
        t = cmd.get("type")
        if t == CommandType.CARD_OPERATION.value:
            self.handle_card_operation(cmd)
        elif t == CommandType.FORMATION.value:
            self.handle_formation(cmd)
        elif t == CommandType.SPECIAL_EVENT.value:
            self.handle_special_event(cmd)
        elif t == CommandType.TIMING.value:
            self.handle_timing(cmd)
        elif t == "delay_ms":
            self.handle_delay(cmd)
        elif t == "force_order_play":
            self.handle_force_order_play(cmd)
        elif t == "or":
            self.handle_or(cmd)
        elif t == "sequence":
            self.handle_sequence(cmd)
        elif t == "raw":
            self.handle_raw(cmd)
        else:
            print(f"Unknown command type: {t}")

    def handle_special_event(self, action):
        # Placeholder for handling special events
        pass

    def handle_card_operation(self, action, card_ops=None):
        """
        增强卡牌操作逻辑，实现三选一、顺序部署和自动刷新，确保顺序和组合灵活。
        针对“同排”时，允许两张卡牌无序但同排部署，遍历所有可能顺序，确保它们最终在同一行；
        “强制顺序上卡”则严格按照命令顺序依次部署所有卡牌。
        """
        # 动态获取所需卡牌顺序
        if card_ops is None:
            card_ops = [action] if action else []
        required_cards = [c["card"] for c in card_ops if "card" in c]
        formation_type = None
        if action and "formation_type" in action:
            formation_type = action["formation_type"]
        elif card_ops and any("formation_type" in c for c in card_ops):
            formation_type = next((c["formation_type"] for c in card_ops if "formation_type" in c), None)
        deployed = []
        batch_count = 0
        if formation_type == FormationType.SAME_ROW.value and len(required_cards) == 2:
            # 同排：两张卡牌无序但需同排
            from itertools import permutations
            found = False
            for order in permutations(required_cards):
                tmp_required = list(order)
                tmp_deployed = []
                tmp_batch_count = 0
                while tmp_required:
                    batch = self.get_next_card_batch()
                    tmp_batch_count += 1
                    if tmp_required[0] in batch:
                        tmp_deployed.append(tmp_required[0])
                        batch.remove(tmp_required[0])
                        tmp_required.pop(0)
                    elif len(tmp_required) > 1 and tmp_required[1] in batch:
                        tmp_deployed.append(tmp_required[1])
                        batch.remove(tmp_required[1])
                        tmp_required.pop(1)
                    else:
                        self.refresh_cards()
                        continue
                # 检查是否同排（假设有 check_same_row 方法）
                if self.check_same_row(tmp_deployed):
                    deployed = tmp_deployed
                    batch_count = tmp_batch_count
                    found = True
                    break
            if not found:
                print("未能找到同排部署方案")
        elif formation_type == FormationType.ORDERED.value:
            # 强制顺序上卡：严格顺序
            while required_cards:
                batch = self.get_next_card_batch()
                batch_count += 1
                if required_cards[0] in batch:
                    deployed.append(required_cards[0])
                    batch.remove(required_cards[0])
                    required_cards.pop(0)
                else:
                    self.refresh_cards()
                    continue
        else:
            # 默认逻辑
            while required_cards:
                batch = self.get_next_card_batch()
                batch_count += 1
                if required_cards[0] in batch:
                    deployed.append(required_cards[0])
                    batch.remove(required_cards[0])
                    required_cards.pop(0)
                elif len(required_cards) > 1 and required_cards[1] in batch:
                    self.refresh_cards()
                    continue
                else:
                    self.refresh_cards()
                    continue
        layout = [deployed, [None]*len(deployed)]
        return layout, {}

    def check_same_row(self, deployed_cards):
        """
        检查传入卡牌是否在同一排，需根据实际车辆布局实现。
        这里假设所有卡牌都能部署到同排，实际应根据车辆状态判断。
        """
        # TODO: 实现真实同排判断逻辑
        return True

    def handle_formation(self, action, card_ops=None):
        """
        处理编队动作，返回布局和特殊位信息
        """
        if not action:
            return None, {}
        formation = action.get("formation")
        cards = action.get("card", [])
        # 仅支持同排，后续可扩展
        if formation == "同排" and card_ops:
            row = [c["card"] for c in card_ops if c["card"] in cards]
            layout = [row, [None]*len(row)]
            return layout, {}
        return None, {}

    def handle_timing(self, action):
        # Placeholder for handling timing actions
        pass

    def handle_delay(self, action):
        import time
        ms = action.get('ms', 0)
        time.sleep(ms / 1000.0)

    def handle_force_order_play(self, action):
        # Placeholder for force order play
        pass

    def handle_or(self, action):
        # Placeholder for handling 'or' actions
        pass

    def handle_sequence(self, action):
        # Placeholder for handling sequence actions
        pass

    def handle_raw(self, action):
        # Placeholder for handling raw actions
        pass

    def sell_card(self, params):
        """
        卖卡操作，占位函数
        params: dict, 包含卡牌信息等
        """
        pass

    def deploy_cards(self, params):
        """
        部署卡牌操作，实际部署逻辑
        params: dict, 结构如 {"layout": [["火灵", "蛇女"], [None, None]], "special": {"top": "宝库"}}
        """
        layout = params.get("layout", [])
        special = params.get("special", {})
        print(f"部署卡牌: 布局={layout}, 特殊位={special}")
        # 这里应调用实际部署逻辑
        # TODO: 调用 GameService 或其他服务实现部署
        pass