import discord
import requests

# Funciones para interactuar con la API de cartas
def create_and_shuffle_deck():
    response = requests.get('https://www.deckofcardsapi.com/api/deck/new/shuffle/?deck_count=1')
    return response.json()

def draw_cards(deck_id, count=1):
    response = requests.get(f'https://www.deckofcardsapi.com/api/deck/{deck_id}/draw/?count={count}')
    return response.json()

# Funciones del juego
def card_value(card):
    """Retorna el valor de la carta."""
    value = card['value']
    if value in ['KING', 'QUEEN', 'JACK']:
        return 10
    elif value == 'ACE':
        return 11  # En caso de tener más de un ace, se ajustará más adelante
    else:
        return int(value)

def hand_value(hand):
    """Retorna el valor total de la mano, ajustando los ases."""
    total = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card['value'] == 'ACE')
    
    while total > 21 and aces:
        total -= 10
        aces -= 1
    
    return total

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Verificar si el juego ha sido inicializado
        if not hasattr(self, 'game_state'):
            self.game_state = 'not_started'

        if message.content.startswith('21'):
            if self.game_state == 'playing':
                await message.channel.send("🚨 Ya estás jugando una partida. Usa 'Quedarse' para terminar la partida actual antes de iniciar una nueva.")
                return
            
            # Crear y barajar un nuevo mazo
            self.deck_data = create_and_shuffle_deck()
            self.deck_id = self.deck_data['deck_id']
            
            # Repartir las cartas iniciales
            self.player_hand = draw_cards(self.deck_id, count=2)['cards']
            self.dealer_hand = draw_cards(self.deck_id, count=2)['cards']
            
            # Mostrar cartas del crupier y del jugador
            await message.channel.send(f'Primera carta del crupier: {self.dealer_hand[0]["image"]}')
            await message.channel.send(f'Primera carta del jugador: {self.player_hand[0]["image"]}')
            await message.channel.send(f'Valor de la primera carta del jugador: {card_value(self.player_hand[0])}')
            
            await message.channel.send(f'Segunda carta del jugador: {self.player_hand[1]["image"]}')
            await message.channel.send(f'Valor de la segunda carta del jugador: {card_value(self.player_hand[1])}')
            
            if hand_value(self.player_hand) == 21:
                await message.channel.send(f'¡Felicidades! ¡Has sacado 21!')
                await message.channel.send(f'Mano del crupier:')
                for card in self.dealer_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Valor total del crupier: {hand_value(self.dealer_hand)}.')
                
                await message.channel.send(f'Tu mano:')
                for card in self.player_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Valor total de tu mano: {hand_value(self.player_hand)}.')
                
                if hand_value(self.dealer_hand) == 21:
                    await message.channel.send("¡Es un empate! Ambos tienen 21.")
                else:
                    await message.channel.send("¡Ganaste el juego!")
                
                self.game_state = 'ended'
            else:
                self.game_state = 'playing'
        
        elif message.content.startswith('Pedir') and self.game_state == 'playing':
            # Pedir una carta para el jugador
            new_card = draw_cards(self.deck_id, count=1)['cards'][0]
            self.player_hand.append(new_card)
            
            player_total = hand_value(self.player_hand)
            
            if player_total > 21:
                await message.channel.send(f'Nueva carta: {new_card["image"]}')
                await message.channel.send(f'¡Te pasaste! Tu mano:')
                for card in self.player_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Total: {player_total}. El crupier gana.')
                self.game_state = 'ended'
            elif player_total == 21:
                await message.channel.send(f'Nueva carta: {new_card["image"]}')
                await message.channel.send(f'¡Felicidades! ¡Has sacado 21!')
                await message.channel.send(f'Tu mano:')
                for card in self.player_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Valor total de tu mano: {player_total}.')
                
                await message.channel.send(f'Mano del crupier:')
                for card in self.dealer_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Valor total del crupier: {hand_value(self.dealer_hand)}.')
                
                if hand_value(self.dealer_hand) == 21:
                    await message.channel.send("¡Es un empate! Ambos tienen 21.")
                else:
                    await message.channel.send("¡Ganaste el juego!")
                
                self.game_state = 'ended'
            else:
                await message.channel.send(f'Nueva carta: {new_card["image"]}')
                await message.channel.send(f'Tu mano:')
                for card in self.player_hand:
                    await message.channel.send(card['image'])
                await message.channel.send(f'Total: {player_total}.')

        elif message.content.startswith('Quedarse') and self.game_state == 'playing':
            # El jugador se queda, jugar la mano del crupier
            dealer_total = hand_value(self.dealer_hand)
            while dealer_total < 17:
                new_card = draw_cards(self.deck_id, count=1)['cards'][0]
                self.dealer_hand.append(new_card)
                dealer_total = hand_value(self.dealer_hand)
            
            player_total = hand_value(self.player_hand)
            dealer_total = hand_value(self.dealer_hand)
            result = self.determine_winner(player_total, dealer_total)
            
            # Mostrar resultados
            await message.channel.send(f'Mano del crupier:')
            for card in self.dealer_hand:
                await message.channel.send(card['image'])
            await message.channel.send(f'Valor total del crupier: {dealer_total}.')
            
            await message.channel.send(f'Tu mano:')
            for card in self.player_hand:
                await message.channel.send(card['image'])
            await message.channel.send(f'Valor total de tu mano: {player_total}.')
            
            await message.channel.send(result)
            self.game_state = 'ended'

        else:
            if self.game_state == 'not_started':
                await message.channel.send("🚨 No has iniciado el juego. Usa el comando `21` para iniciar una partida.")
            elif self.game_state == 'playing':
                await message.channel.send("🚨 El juego ya está en curso. Usa 'Pedir' para pedir una carta o 'Quedarse' para terminar el turno.")

    def determine_winner(self, player_total, dealer_total):
        """Determina el ganador."""
        if player_total > 21:
            return "¡Te pasaste! El crupier gana."
        elif dealer_total > 21:
            return "¡El crupier se pasó! Tú ganas."
        elif player_total > dealer_total:
            return "¡Tú ganas!"
        elif player_total < dealer_total:
            return "El crupier gana."
        else:
            return "¡Es un empate!"

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run('') # Replace with your own token.