import unittest
from unittest.mock import patch, MagicMock
import uuid
from app.bracket_logic import generate_bracket

class TestGenerateBracket(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_data = {'competitors': [], 'brackets': {}}
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_empty_competitors(self, mock_get, mock_save):
        """Test bracket generation with no competitors."""
        self.mock_data['competitors'] = []
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        mock_get.assert_called_once()
        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        self.assertEqual(saved_data['brackets'], {'upper': [], 'lower': []})
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_single_competitor(self, mock_get, mock_save):
        """Test bracket generation with only one competitor."""
        self.mock_data['competitors'] = [{'id': '1', 'name': 'Player1', 'pp': 100}]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        mock_get.assert_called_once()
        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        self.assertEqual(saved_data['brackets'], {'upper': [], 'lower': []})
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_two_competitors(self, mock_get, mock_save):
        """Test bracket generation with two competitors."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        mock_get.assert_called_once()
        mock_save.assert_called_once()
        saved_data = mock_save.call_args[0][0]
        
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 1)
        
        match = saved_data['brackets']['upper'][0][0]
        self.assertEqual(match['player1']['name'], 'Player2')  # Higher PP first
        self.assertEqual(match['player2']['name'], 'Player1')
        self.assertIsNone(match['winner'])
        self.assertIsNotNone(match['id'])
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_four_competitors(self, mock_get, mock_save):
        """Test bracket generation with four competitors (power of 2)."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200},
            {'id': '3', 'name': 'Player3', 'pp': 300},
            {'id': '4', 'name': 'Player4', 'pp': 400}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 2)
        
        matches = saved_data['brackets']['upper'][0]
        
        # Verify snake seeding: 1 vs 4, 2 vs 3
        self.assertEqual(matches[0]['player1']['name'], 'Player4')  # Seed 1 (highest PP)
        self.assertEqual(matches[0]['player2']['name'], 'Player1')  # Seed 4 (lowest PP)
        self.assertEqual(matches[1]['player1']['name'], 'Player3')  # Seed 2
        self.assertEqual(matches[1]['player2']['name'], 'Player2')  # Seed 3
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_three_competitors_with_bye(self, mock_get, mock_save):
        """Test bracket generation with three competitors requiring one BYE."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200},
            {'id': '3', 'name': 'Player3', 'pp': 300}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 2)
        
        matches = saved_data['brackets']['upper'][0]
        
        # One match should have a BYE
        bye_matches = [m for m in matches if m['player1']['name'] == 'BYE' or m['player2']['name'] == 'BYE']
        self.assertEqual(len(bye_matches), 1)
        
        # BYE match should have a winner automatically
        bye_match = bye_matches[0]
        self.assertIsNotNone(bye_match['winner'])
        self.assertNotEqual(bye_match['winner']['name'], 'BYE')
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_seeding_by_pp(self, mock_get, mock_save):
        """Test that competitors are properly seeded by PP (Performance Points)."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 50},
            {'id': '2', 'name': 'Player2', 'pp': 300},
            {'id': '3', 'name': 'Player3', 'pp': 100},
            {'id': '4', 'name': 'Player4', 'pp': 200}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        matches = saved_data['brackets']['upper'][0]
        
        # Highest PP should be seed 1 and face lowest seed
        highest_pp_player = max(self.mock_data['competitors'], key=lambda x: x['pp'])
        lowest_pp_player = min(self.mock_data['competitors'], key=lambda x: x['pp'])
        
        # Find match with highest PP player
        match_with_highest = None
        for match in matches:
            if (match['player1']['name'] == highest_pp_player['name'] or 
                match['player2']['name'] == highest_pp_player['name']):
                match_with_highest = match
                break
        
        self.assertIsNotNone(match_with_highest)
        # Verify they're paired together (snake seeding)
        players_in_match = [match_with_highest['player1']['name'], match_with_highest['player2']['name']]
        self.assertIn(lowest_pp_player['name'], players_in_match)
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_competitors_with_no_pp(self, mock_get, mock_save):
        """Test bracket generation with competitors having no PP value."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1'},  # No PP
            {'id': '2', 'name': 'Player2', 'pp': 200},
            {'id': '3', 'name': 'Player3', 'pp': None},  # None PP
            {'id': '4', 'name': 'Player4', 'pp': 100}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        # Should not crash and should create matches
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 2)
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_removes_existing_grand_finals(self, mock_get, mock_save):
        """Test that existing grand finals are removed when generating new bracket."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        self.mock_data['brackets'] = {'grand_finals': {'some': 'data'}}
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        self.assertNotIn('grand_finals', saved_data['brackets'])
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_match_structure(self, mock_get, mock_save):
        """Test that generated matches have correct structure."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        match = saved_data['brackets']['upper'][0][0]
        
        # Verify match structure
        self.assertIn('id', match)
        self.assertIn('player1', match)
        self.assertIn('player2', match)
        self.assertIn('winner', match)
        self.assertIsInstance(match['id'], str)
        
        # Verify UUID format
        try:
            uuid.UUID(match['id'])
        except ValueError:
            self.fail("Match ID is not a valid UUID")
    
    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_eight_competitors(self, mock_get, mock_save):
        """Test bracket generation with eight competitors."""
        self.mock_data['competitors'] = [
            {'id': str(i), 'name': f'Player{i}', 'pp': i * 100} 
            for i in range(1, 9)
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 4)
        
        # Verify no BYEs needed
        matches = saved_data['brackets']['upper'][0]
        for match in matches:
            self.assertNotEqual(match['player1']['name'], 'BYE')
            self.assertNotEqual(match['player2']['name'], 'BYE')
            self.assertIsNone(match['winner'])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_creates_empty_lower_bracket(self, mock_get, mock_save):
        """Test that lower bracket is initialized as empty."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        self.assertIn('lower', saved_data['brackets'])
        self.assertEqual(saved_data['brackets']['lower'], [])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_preserves_existing_lower_bracket(self, mock_get, mock_save):
        """Test that existing lower bracket data is preserved when regenerating upper bracket."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        self.mock_data['brackets'] = {
            'upper': [],
            'lower': [{'some': 'existing_data'}]
        }
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        # Should preserve existing lower bracket when regenerating
        self.assertEqual(saved_data['brackets']['lower'], [{'some': 'existing_data'}])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_clears_existing_upper_bracket(self, mock_get, mock_save):
        """Test that existing upper bracket is completely replaced."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        self.mock_data['brackets'] = {
            'upper': [{'old': 'data'}],
            'lower': []
        }
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        # Should completely replace upper bracket
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 1)
        self.assertNotIn('old', str(saved_data['brackets']['upper']))

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_sixteen_competitors_structure(self, mock_get, mock_save):
        """Test bracket structure with 16 competitors (multiple rounds)."""
        self.mock_data['competitors'] = [
            {'id': str(i), 'name': f'Player{i}', 'pp': i * 50} 
            for i in range(1, 17)
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        # Should create first round with 8 matches
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 8)
        
        # Verify no BYEs needed with 16 competitors
        matches = saved_data['brackets']['upper'][0]
        for match in matches:
            self.assertNotEqual(match['player1']['name'], 'BYE')
            self.assertNotEqual(match['player2']['name'], 'BYE')

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_odd_number_with_multiple_byes(self, mock_get, mock_save):
        """Test bracket generation with odd number requiring multiple BYEs."""
        self.mock_data['competitors'] = [
            {'id': str(i), 'name': f'Player{i}', 'pp': i * 100} 
            for i in range(1, 6)  # 5 competitors
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        matches = saved_data['brackets']['upper'][0]
        
        # Should create 4 matches (next power of 2 / 2)
        self.assertEqual(len(matches), 4)
        
        # Should have 3 BYE matches (8 - 5 = 3 BYEs needed)
        bye_matches = [m for m in matches if m['player1']['name'] == 'BYE' or m['player2']['name'] == 'BYE']
        self.assertEqual(len(bye_matches), 3)
        
        # All BYE matches should have winners
        for bye_match in bye_matches:
            self.assertIsNotNone(bye_match['winner'])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_handles_duplicate_pp_values(self, mock_get, mock_save):
        """Test bracket generation with competitors having identical PP values."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 100},
            {'id': '3', 'name': 'Player3', 'pp': 100},
            {'id': '4', 'name': 'Player4', 'pp': 100}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        
        # Should not crash and create proper structure
        self.assertEqual(len(saved_data['brackets']['upper']), 1)
        self.assertEqual(len(saved_data['brackets']['upper'][0]), 2)
        
        # All matches should have valid structure
        matches = saved_data['brackets']['upper'][0]
        for match in matches:
            self.assertIsNotNone(match['player1'])
            self.assertIsNotNone(match['player2'])
            self.assertIsNone(match['winner'])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_removes_all_existing_finals(self, mock_get, mock_save):
        """Test that all types of finals are removed when generating new bracket."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100},
            {'id': '2', 'name': 'Player2', 'pp': 200}
        ]
        self.mock_data['brackets'] = {
            'upper': [],
            'lower': [],
            'grand_finals': {'match': 'data'},
            'grand_finals_reset': {'reset': 'data'}
        }
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        self.assertNotIn('grand_finals', saved_data['brackets'])
        self.assertNotIn('grand_finals_reset', saved_data['brackets'])

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_unique_match_ids(self, mock_get, mock_save):
        """Test that all generated matches have unique IDs."""
        self.mock_data['competitors'] = [
            {'id': str(i), 'name': f'Player{i}', 'pp': i * 100} 
            for i in range(1, 9)  # 8 competitors
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        matches = saved_data['brackets']['upper'][0]
        
        # Collect all match IDs
        match_ids = [match['id'] for match in matches]
        
        # Verify all IDs are unique
        self.assertEqual(len(match_ids), len(set(match_ids)))
        
        # Verify all are valid UUIDs
        for match_id in match_ids:
            try:
                uuid.UUID(match_id)
            except ValueError:
                self.fail(f"Match ID {match_id} is not a valid UUID")

    @patch('app.bracket_logic.save_tournament_data')
    @patch('app.bracket_logic.get_tournament_data')
    def test_generate_bracket_player_data_preservation(self, mock_get, mock_save):
        """Test that all player data is preserved in matches."""
        self.mock_data['competitors'] = [
            {'id': '1', 'name': 'Player1', 'pp': 100, 'extra': 'data1'},
            {'id': '2', 'name': 'Player2', 'pp': 200, 'extra': 'data2'}
        ]
        mock_get.return_value = self.mock_data
        
        generate_bracket()
        
        saved_data = mock_save.call_args[0][0]
        match = saved_data['brackets']['upper'][0][0]
        
        # Verify all competitor data is preserved
        self.assertEqual(match['player1']['id'], '2')
        self.assertEqual(match['player1']['name'], 'Player2')
        self.assertEqual(match['player1']['pp'], 200)
        self.assertEqual(match['player1']['extra'], 'data2')
        
        self.assertEqual(match['player2']['id'], '1')
        self.assertEqual(match['player2']['name'], 'Player1')
        self.assertEqual(match['player2']['pp'], 100)
        self.assertEqual(match['player2']['extra'], 'data1')


# Import advance_round_if_ready for comprehensive testing
from app.bracket_logic import advance_round_if_ready


class TestAdvanceRoundIfReady(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_data = {
            'competitors': [
                {'id': '1', 'name': 'Player1', 'pp': 100},
                {'id': '2', 'name': 'Player2', 'pp': 200},
                {'id': '3', 'name': 'Player3', 'pp': 300},
                {'id': '4', 'name': 'Player4', 'pp': 400}
            ],
            'brackets': {'upper': [], 'lower': []}
        }
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_advance_round_no_upper_bracket(self, mock_save):
        """Test advance_round_if_ready with no upper bracket."""
        data = {'competitors': [], 'brackets': {}}
        
        advance_round_if_ready(data)
        
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_advance_round_incomplete_upper_round(self, mock_save):
        """Test that incomplete upper bracket round doesn't advance."""
        upper_round = [
            {
                'id': '1',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'id': '2', 'name': 'Player2', 'pp': 200},
                'winner': {'id': '2', 'name': 'Player2', 'pp': 200}
            },
            {
                'id': '2',
                'player1': {'id': '3', 'name': 'Player3', 'pp': 300},
                'player2': {'id': '4', 'name': 'Player4', 'pp': 400},
                'winner': None  # Incomplete match
            }
        ]
        
        data = {
            'competitors': self.mock_data['competitors'],
            'brackets': {'upper': [upper_round], 'lower': []}
        }
        
        advance_round_if_ready(data)
        
        # Should not advance - still only one round
        self.assertEqual(len(data['brackets']['upper']), 1)
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_advance_complete_upper_round(self, mock_save):
        """Test advancing complete upper bracket round."""
        upper_round = [
            {
                'id': '1',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'id': '2', 'name': 'Player2', 'pp': 200},
                'winner': {'id': '2', 'name': 'Player2', 'pp': 200}
            },
            {
                'id': '2',
                'player1': {'id': '3', 'name': 'Player3', 'pp': 300},
                'player2': {'id': '4', 'name': 'Player4', 'pp': 400},
                'winner': {'id': '4', 'name': 'Player4', 'pp': 400}
            }
        ]
        
        data = {
            'competitors': self.mock_data['competitors'],
            'brackets': {'upper': [upper_round], 'lower': []}
        }
        
        advance_round_if_ready(data)
        
        # Should advance to next upper round
        self.assertEqual(len(data['brackets']['upper']), 2)
        next_round = data['brackets']['upper'][1]
        self.assertEqual(len(next_round), 1)  # One match in finals
        
        # Verify snake seeding in next round
        match = next_round[0]
        self.assertEqual(match['player1']['name'], 'Player4')  # Higher seed
        self.assertEqual(match['player2']['name'], 'Player2')  # Lower seed
        
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_advance_moves_losers_to_lower_bracket(self, mock_save):
        """Test that losers from upper bracket are moved to lower bracket."""
        upper_round = [
            {
                'id': '1',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'id': '2', 'name': 'Player2', 'pp': 200},
                'winner': {'id': '2', 'name': 'Player2', 'pp': 200}
            },
            {
                'id': '2',
                'player1': {'id': '3', 'name': 'Player3', 'pp': 300},
                'player2': {'id': '4', 'name': 'Player4', 'pp': 400},
                'winner': {'id': '4', 'name': 'Player4', 'pp': 400}
            }
        ]
        
        data = {
            'competitors': self.mock_data['competitors'],
            'brackets': {'upper': [upper_round], 'lower': []}
        }
        
        advance_round_if_ready(data)
        
        # Should create lower bracket round with losers
        self.assertEqual(len(data['brackets']['lower']), 1)
        lower_round = data['brackets']['lower'][0]
        self.assertEqual(len(lower_round), 1)  # One match
        
        # Verify losers are in lower bracket
        lower_match = lower_round[0]
        loser_names = {lower_match['player1']['name'], lower_match['player2']['name']}
        self.assertEqual(loser_names, {'Player1', 'Player3'})
        
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_create_grand_finals(self, mock_save):
        """Test creation of grand finals when both brackets have single winners."""
        upper_finals = [
            {
                'id': '1',
                'player1': {'id': '2', 'name': 'Player2', 'pp': 200},
                'player2': {'id': '4', 'name': 'Player4', 'pp': 400},
                'winner': {'id': '4', 'name': 'Player4', 'pp': 400}
            }
        ]
        
        lower_finals = [
            {
                'id': '2',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'id': '3', 'name': 'Player3', 'pp': 300},
                'winner': {'id': '3', 'name': 'Player3', 'pp': 300}
            }
        ]
        
        data = {
            'competitors': self.mock_data['competitors'],
            'brackets': {'upper': [upper_finals], 'lower': [lower_finals]}
        }
        
        advance_round_if_ready(data)
        
        # Should create grand finals
        self.assertIn('grand_finals', data['brackets'])
        grand_finals = data['brackets']['grand_finals']
        
        self.assertEqual(grand_finals['player1']['name'], 'Player4')  # Upper winner
        self.assertEqual(grand_finals['player2']['name'], 'Player3')  # Lower winner
        self.assertIsNone(grand_finals['winner'])
        self.assertTrue(grand_finals['is_grand_finals'])
        self.assertIsNotNone(grand_finals['id'])
        
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_advance_with_byes_in_upper_bracket(self, mock_save):
        """Test advancing upper bracket round with BYE matches."""
        upper_round = [
            {
                'id': '1',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'name': 'BYE', 'id': None},
                'winner': {'id': '1', 'name': 'Player1', 'pp': 100}
            },
            {
                'id': '2',
                'player1': {'id': '2', 'name': 'Player2', 'pp': 200},
                'player2': {'id': '3', 'name': 'Player3', 'pp': 300},
                'winner': {'id': '3', 'name': 'Player3', 'pp': 300}
            }
        ]
        
        data = {
            'competitors': self.mock_data['competitors'],
            'brackets': {'upper': [upper_round], 'lower': []}
        }
        
        advance_round_if_ready(data)
        
        # Should advance upper bracket
        self.assertEqual(len(data['brackets']['upper']), 2)
        
        # Should only move real players to lower bracket (not BYEs)
        self.assertEqual(len(data['brackets']['lower']), 1)
        lower_round = data['brackets']['lower'][0]
        
        # Only Player2 should be in lower bracket (Player1 won vs BYE)
        self.assertEqual(len(lower_round), 1)
        lower_match = lower_round[0]
        player_names = {lower_match['player1']['name'], lower_match['player2']['name']}
        self.assertIn('Player2', player_names)
        self.assertNotIn('BYE', player_names)
        
        mock_save.assert_called_once_with(data)
    
    @patch('app.bracket_logic.save_tournament_data')
    def test_snake_seeding_in_advanced_upper_round(self, mock_save):
        """Test that snake seeding is applied correctly in advanced upper rounds."""
        upper_round = [
            {
                'id': '1',
                'player1': {'id': '1', 'name': 'Player1', 'pp': 100},
                'player2': {'id': '2', 'name': 'Player2', 'pp': 200},
                'winner': {'id': '2', 'name': 'Player2', 'pp': 200}
            },
            {
                'id': '2',
                'player1': {'id': '3', 'name': 'Player3', 'pp': 300},
                'player2': {'id': '4', 'name': 'Player4', 'pp': 400},
                'winner': {'id': '4', 'name': 'Player4', 'pp': 400}
            },
            {
                'id': '3',
                'player1': {'id': '5', 'name': 'Player5', 'pp': 500},
                'player2': {'id': '6', 'name': 'Player6', 'pp': 600},
                'winner': {'id': '6', 'name': 'Player6', 'pp': 600}
            },
            {
                'id': '4',
                'player1': {'id': '7', 'name': 'Player7', 'pp': 700},
                'player2': {'id': '8', 'name': 'Player8', 'pp': 800},
                'winner': {'id': '8', 'name': 'Player8', 'pp': 800}
            }
        ]
        
        all_competitors = [
            {'id': str(i), 'name': f'Player{i}', 'pp': i * 100}
            for i in range(1, 9)
        ]
        
        data = {
            'competitors': all_competitors,
            'brackets': {'upper': [upper_round], 'lower': []}
        }
        
        advance_round_if_ready(data)
        
        # Check snake seeding in next round
        next_round = data['brackets']['upper'][1]
        self.assertEqual(len(next_round), 2)
        
        # Highest seed (Player8) should face lowest seed (Player2)
        # Second highest (Player6) should face second lowest (Player4)
        match1 = next_round[0]
        match2 = next_round[1]
        
        # Verify seeding pattern
        self.assertEqual(match1['player1']['name'], 'Player8')  # Highest PP
        self.assertEqual(match1['player2']['name'], 'Player2')  # Lowest PP among winners
        self.assertEqual(match2['player1']['name'], 'Player6')  # Second highest PP
        self.assertEqual(match2['player2']['name'], 'Player4')  # Second lowest PP among winners
        
        mock_save.assert_called_once_with(data)


if __name__ == '__main__':
    unittest.main()