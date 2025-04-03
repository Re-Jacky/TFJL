import unittest
from app.utils.command_parser import CommandParser
from pathlib import Path


## run: python -m unittest app.tests.test_command_parser

class TestCommandParser(unittest.TestCase):
    def test_case_1(self):
        file_path = Path(__file__).parent.resolve() / 'TC-1.txt'
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        def find_command_by_index(chain, index):
            for command in chain:
                if command["index"] == index:
                    return command['commands']
            return None

        result = CommandParser(content).parse_script()
        self.assertEqual(result["formation"],
                         ['骨弓', '火灵', '萌萌', '绿弓', '魂精灵', '土灵', '酋长', '宝库', '冰精灵', '蛇女'])
        self.assertEqual(result["enhanced_cards"], ["土灵"])
        self.assertEqual(result["main_vehicle"], "未设置")
        self.assertEqual(result["sub_vehicle"], "未设置")

        # check command chains
        chain = result["command_chain"]
        self.assertEqual(find_command_by_index(chain, 1), [
            {
                "type": "formation",
                "formation": "同排",
                'card': ['火灵蛇女']  ## TODO: should be ['火灵', '蛇女']
            },
            {
                "type": "card_op",
                "operation": "上",
                "card": "火灵",
                "level": None
            },
            {
                "type": "card_op",
                "operation": "上",
                "card": "蛇女",
                "level": None
            },
            {
                "type": "card_op",
                "operation": "上",
                "card": "宝库",
                "level": None
            }
        ])

        self.assertEqual(find_command_by_index(chain, 2), [
            {'type': 'card_op', 'operation': '预备手牌', 'card': '骨弓', 'level': None},
        ])

        self.assertEqual(find_command_by_index(chain, 5), [
            {
                'type': 'card_op',
                'operation': '弃牌出牌',
                'card': '冰精灵',
                'level': None
            },
            {
                'card': '火灵',
                'level': '满',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '蛇女',
                'level': '满',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '骨弓',
                'level': '满',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '绿弓',
                'level': '满',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '萌萌',
                'level': '3级',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '酋长',
                'level': '满',
                'operation': '上',
                'type': 'card_op'
            },
            {
                'card': '宝库',
                'level': '不满',
                'operation': '上',
                'type': 'card_op'
            }
        ])

        self.assertEqual(find_command_by_index(chain, 38), [
            {'type': 'special', 'event': '关闭验光', 'commands': []}
        ])

        self.assertEqual(find_command_by_index(chain, 41),
                         [{'card': '', 'level': None, 'operation': '验卡补星', 'type': 'card_op'},
                          {'card': '宝库', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '火灵', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '蛇女', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '萌萌', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '酋长', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '绿弓', 'level': '满', 'operation': '上', 'type': 'card_op'},
                          {'card': '骨弓', 'level': '满', 'operation': '上', 'type': 'card_op'}]
                         )

        self.assertEqual(find_command_by_index(chain, 49), [
            {'pattern': '时钟秒', 'second': 10, 'type': 'timing'},
            {'count': 100,
             'interval': 1.5,
             'pattern': '每',
             'target': '冰精灵',
             'type': 'timing'}])

        self.assertEqual(find_command_by_index(chain, 51), [{'commands': [], 'event': '停球', 'type': 'special'}])

        self.assertEqual(find_command_by_index(chain, 71), [
            {'card': None, 'formation': '同排取消', 'type': 'formation'},
            {'card': '骨弓', 'level': None, 'operation': '下',
             'type': 'card_op'},
            {'card': '土灵', 'level': '满', 'operation': '上',
             'type': 'card_op'}])

        self.assertEqual(find_command_by_index(chain, 79), [
            {'card': '火灵', 'level': None, 'operation': '下', 'type': 'card_op'},
            {'card': '骨弓', 'level': None, 'operation': '预备手牌', 'type': 'card_op'}])


if __name__ == "__main__":
    unittest.main()
