import random
from playcard import make_deck

CARD_VALUES = {
    'A': 11,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'T': 10,
    'J': 10,
    'Q': 10,
    'K': 10,
}

def calculate_hand_value(hand):
    """计算手牌点数，智能处理A的1/11转换（与标准版一致）"""
    value, aces = 0, 0
    for card in hand:
        rank = card[0]
        value += CARD_VALUES[rank]
        aces += rank == 'A'
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def new_game(session):
    """
    欧式规则初始化：
    1. 庄家只发1张明牌，无暗牌
    2. 玩家发2张牌
    3. 开局不检查庄家Blackjack（不可能）
    """
    deck = make_deck()
    random.shuffle(deck)
    
    # 发牌顺序：玩家→玩家→庄家（欧式规则）
    card1 = deck.pop()  # 玩家第1张
    card2 = deck.pop()  # 玩家第2张
    card3 = deck.pop()  # 庄家第1张（唯一明牌）
    
    player_hand = [card1, card2]
    dealer_hand = [card3]  # 欧式：初始只有1张牌
    
    player_value = calculate_hand_value(player_hand)
    dealer_value = calculate_hand_value(dealer_hand)
    
    # 欧式：开局无游戏结束状态，不检查庄家BJ
    session['game_state'] = {
        'deck': deck,
        'dealer_hand': dealer_hand,
        'player_hand': player_hand,
        'dealer_value': dealer_value,
        'player_value': player_value,
        'message': None,
        'message_class': '',
    }

def game_update(session, action):
    """
    处理玩家操作，严格遵循欧式规则：
    1. 玩家先完成所有操作（Hit/Stand）
    2. 玩家停牌后，庄家才抽第2张牌
    3. 自然Blackjack优先级最高
    """
    game_state = session.get('game_state', {})
    if not game_state:
        return new_game(session)
    
    deck = game_state['deck']
    dealer_hand = game_state['dealer_hand']
    player_hand = game_state['player_hand']
    
    if action == 'hit':
        # 玩家要牌
        card = deck.pop()
        player_hand.append(card)
        player_value = calculate_hand_value(player_hand)
        game_state['player_value'] = player_value
        
        # 玩家爆牌：游戏直接结束，庄家无需补牌
        if player_value > 21:
            game_state['dealer_value'] = calculate_hand_value(dealer_hand)
            game_state['message'] = 'You busted! Dealer wins.'
            game_state['message_class'] = 'lose-message'
    
    elif action == 'stand':
        # 玩家停牌，进入庄家回合
        player_value = game_state['player_value']
        
        # 欧式规则核心：玩家停牌后，庄家才抽取第2张牌
        if len(dealer_hand) == 1:
            dealer_hand.append(deck.pop())
        
        # 庄家按规则补牌：点数<17必须要牌
        dealer_value = calculate_hand_value(dealer_hand)
        while dealer_value < 17:
            dealer_hand.append(deck.pop())
            dealer_value = calculate_hand_value(dealer_hand)
        
        game_state['dealer_value'] = dealer_value
        
        # 胜负判断（优先级从高到低）
        # 1. 检查自然Blackjack（最先两张牌组成的21点）
        player_natural = (len(player_hand) == 2 and player_value == 21)
        dealer_natural = (len(dealer_hand) == 2 and dealer_value == 21)
        
        if dealer_natural:
            if player_natural:
                game_state['message'] = "It's a tie! Both have natural Blackjack."
                game_state['message_class'] = 'tie-message'
            else:
                game_state['message'] = 'Dealer has natural Blackjack! You lose.'
                game_state['message_class'] = 'lose-message'
        # 2. 玩家爆牌（已在hit分支处理，此处为冗余保护）
        elif player_value > 21:
            game_state['message'] = 'You busted! Dealer wins.'
            game_state['message_class'] = 'lose-message'
        # 3. 庄家爆牌
        elif dealer_value > 21:
            game_state['message'] = 'Dealer busted! You win!'
            game_state['message_class'] = 'win-message'
        # 4. 点数比较
        elif dealer_value > player_value:
            game_state['message'] = 'Dealer wins!'
            game_state['message_class'] = 'lose-message'
        elif dealer_value < player_value:
            game_state['message'] = 'You win!'
            game_state['message_class'] = 'win-message'
        else:
            game_state['message'] = "It's a tie!"
            game_state['message_class'] = 'tie-message'
    
    session.modified = True