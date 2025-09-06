from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView   # <-- added
from kivy.core.window import Window          # <-- added
from kivy.graphics import Color, Line
from kivy.clock import Clock

# =========================
# ---- HELP / HOW-TO TEXT
# =========================
HELP_TEXT = """
Ultimate Tic-Tac-Toe – How to Play

 Introduction
Ultimate Tic-Tac-Toe expands the classic game into 9 tic-tac-toe boards arranged in a 3×3 grid.

 Setup
- Two players: X and O
- X always starts
- Each turn, you must play inside one of the 9 small boards.

 Rules
1) On your turn, tap a cell to place your mark (X/O).
2) The cell you choose sends your opponent to the board at that same cell index
   (e.g., if you play top-right, your opponent must play in the top-right board).
3) If the required board is already won or full, your opponent may play in ANY unfinished board.
4) Win a small board by getting 3 in a row (just like normal tic-tac-toe).
5) Win the whole game by winning 3 small boards in a row on the big (meta) board.

 Tips
- Think ahead: your move forces your opponent’s next board.
- Don’t send your opponent to an easy winning board.
- Balance offense and defense.
- Corners and center boards are often strong positions.

App UI
- Yellow highlight = the active board(s) you can play in.
- You are X (blue); AI is O (red).
- Use Undo to take back both your and AI’s last moves.
- Restart starts a fresh game.
"""

# =========================
# ---- GAME LOGIC (unchanged)
# =========================
main_board = [' '] * 81
win_board = [' '] * 9
current_player = 'X'
active_board = None
history = []

BASE_DEPTH = 3
MID_DEPTH = 4
LATE_DEPTH = 5

WIN_LINES = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6)
]

def board_cell_to_index(board_idx, cell_idx): return board_idx*9+cell_idx
def small_board_slice(board_idx): return main_board[board_idx*9:board_idx*9+9]
def small_board_is_full(board_idx): return all(c!=' ' for c in small_board_slice(board_idx))
def small_board_available(board_idx): return win_board[board_idx]==' ' and any(c==' ' for c in small_board_slice(board_idx))

def _check_3x3_winner(cells):
    for a,b,c in WIN_LINES:
        if cells[a] != ' ' and cells[a]==cells[b]==cells[c]:
            return cells[a]
    if all(x!=' ' for x in cells): return 'T'
    return ' '

def check_small_win(board_idx):
    result=_check_3x3_winner(small_board_slice(board_idx))
    if result!=' ': win_board[board_idx]=result
    return win_board[board_idx]

def check_global_win():
    for a,b,c in WIN_LINES:
        line=(win_board[a],win_board[b],win_board[c])
        if line[0] in ('X','O') and line[0]==line[1]==line[2]:
            return line[0]
    if all(x!=' ' for x in win_board): return 'T'
    if all(small_board_is_full(i) or win_board[i]!=' ' for i in range(9)): return 'T'
    return ' '

def get_valid_moves(act_board):
    moves=[]
    if act_board is not None and small_board_available(act_board):
        for i,v in enumerate(small_board_slice(act_board)):
            if v==' ': moves.append((act_board,i))
        return moves
    for b in range(9):
        if small_board_available(b):
            for i,v in enumerate(small_board_slice(b)):
                if v==' ': moves.append((b,i))
    return moves

def apply_move(board_idx, cell_idx, player):
    global active_board
    history.append((board_idx, cell_idx, player, active_board))
    main_board[board_cell_to_index(board_idx,cell_idx)]=player
    check_small_win(board_idx)
    next_board=cell_idx
    if next_board is not None and not small_board_available(next_board):
        next_board=None
    return next_board

def undo_last_move():
    global active_board,current_player
    if not history: return
    board_idx,cell_idx,player,prev_active=history.pop()
    main_board[board_cell_to_index(board_idx,cell_idx)]=' '
    win_board[board_idx]=_check_3x3_winner(small_board_slice(board_idx))
    active_board=prev_active; current_player=player

def line_score_3(a,b,c,player):
    opp='O' if player=='X' else 'X'; line=[a,b,c]
    if line.count(player)==3: return 10000
    if line.count(opp)==3: return -10000
    if player in line and opp in line: return 0
    score=0
    if line.count(player)==2: score+=150
    if line.count(player)==1: score+=40
    if line.count(opp)==2: score-=170
    if line.count(opp)==1: score-=45
    return score

def score_small_board(cells,player):
    opp='O' if player=='X' else 'X'; result=_check_3x3_winner(cells)
    if result==player: return 300
    if result==opp: return -350
    if result=='T': return 0
    score=0
    for a,b,c in WIN_LINES:
        trio=(cells[a],cells[b],cells[c])
        if player in trio and opp in trio: continue
        if trio.count(player)==2: score+=15
        elif trio.count(player)==1: score+=5
        elif trio.count(opp)==2: score-=17
        elif trio.count(opp)==1: score-=6
    return score

def evaluate(player_pov='X'):
    g=check_global_win()
    if g==player_pov: return 1_000_000
    elif g=='T': return 0
    elif g!=' ': return -1_000_000
    score=0
    for a,b,c in WIN_LINES:
        score+=line_score_3(win_board[a],win_board[b],win_board[c],player_pov)
    for b in range(9):
        if win_board[b]==' ': score+=score_small_board(small_board_slice(b),player_pov)
    return score

def minimax(player,act_board,depth,alpha,beta):
    g=check_global_win()
    if depth==0 or g in ('X','O','T'): return evaluate('O'),None
    is_maximizing=(player=='O'); moves=get_valid_moves(act_board)
    if not moves: return evaluate('O'),None
    best_move=None
    if is_maximizing:
        value=-float('inf')
        for (b,c) in moves:
            next_board=apply_move(b,c,player)
            sc,_=minimax('X',next_board,depth-1,alpha,beta)
            undo_last_move()
            if sc>value: value=sc; best_move=(b,c)
            alpha=max(alpha,value)
            if beta<=alpha: break
        return value,best_move
    else:
        value=float('inf')
        for (b,c) in moves:
            next_board=apply_move(b,c,player)
            sc,_=minimax('O',next_board,depth-1,alpha,beta)
            undo_last_move()
            if sc<value: value=sc; best_move=(b,c)
            beta=min(beta,value)
            if beta<=alpha: break
        return value,best_move

def choose_search_depth():
    empties=main_board.count(' ')
    if empties>60: return BASE_DEPTH
    if empties>30: return MID_DEPTH
    return LATE_DEPTH

def ui_idx_to_rc(idx): return idx//9, idx%9
def rc_to_bc(r,c): return (r//3)*3+(c//3), (r%3)*3+(c%3)

# =========================
# ---- Button with Border ----
# =========================
class CellButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_border, size=self.update_border)

    def update_border(self,*args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(0,0,0,0.4)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=1)

# =========================
# ---- Overlay for Big Dark Lines ----
# =========================
class GridOverlay(Widget):
    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.target.bind(pos=self._sync, size=self._sync)
        Clock.schedule_once(self._sync, 0)

    def _sync(self, *args):
        self.pos = self.target.pos
        self.size = self.target.size
        self._draw()

    def _draw(self,*args):
        self.canvas.clear()
        with self.canvas:
            x,y = self.pos
            w,h = self.size
            cw = w/9; ch = h/9
            Color(0,0,0,1)  # solid black
            for i in [3,6]:
                Line(points=[x+i*cw,y,x+i*cw,y+h], width=3)
                Line(points=[x,y+i*ch,x+w,y+i*ch], width=3)

# =========================
# ---- Board ----
# =========================
class UltimateTTT(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols=9; self.rows=9; self.buttons=[]
        self.size_hint=(None,None)
        self.bind(size=self.refresh_ui)

        for i in range(81):
            btn=CellButton(text=" ",font_size=40,
                       background_normal='',
                       background_color=(0.96,0.96,0.96,1),
                       color=(0,0,0,1))
            btn.bind(on_press=self.on_cell_press)
            self.add_widget(btn); self.buttons.append(btn)

    def refresh_ui(self,*args):
        cell_side = min(self.width/9, self.height/9)
        fsize = max(int(cell_side*0.55), 24)
        for idx in range(81):
            r,c=ui_idx_to_rc(idx); b,cell=rc_to_bc(r,c)
            val=main_board[board_cell_to_index(b,cell)]; btn=self.buttons[idx]
            btn.text=val if val!=' ' else " "
            btn.font_size=fsize
            btn.color=(0,0,1,1) if val=='X' else ((1,0,0,1) if val=='O' else (0,0,0,1))
            btn.background_color=(1,1,0.78,1) if (active_board is None or b==active_board) else (0.96,0.96,0.96,1)

    def on_cell_press(self,instance):
        global current_player,active_board
        idx=self.buttons.index(instance); r,c=ui_idx_to_rc(idx); b,cell=rc_to_bc(r,c)
        if (b,cell) not in get_valid_moves(active_board): return
        active_board=apply_move(b,cell,'X'); self.refresh_ui(); current_player='O'; self.check_winner()
        if current_player=='O':
            depth=choose_search_depth()
            _,move=minimax('O',active_board,depth,-float('inf'),float('inf'))
            if move: mb,mc=move; active_board=apply_move(mb,mc,'O')
            self.refresh_ui(); current_player='X'; self.check_winner()

    def check_winner(self):
        g=check_global_win()
        if g in ('X','O','T'):
            msg="You win!" if g=='X' else ("AI wins!" if g=='O' else "It's a draw!")
            Popup(title="Game Over",content=Label(text=msg,font_size=72),size_hint=(0.6,0.4)).open()

# =========================
# ---- App ----
# =========================
class UltimateTTTApp(App):
    def build(self):
        root=BoxLayout(orientation="vertical")
        board_area=FloatLayout(size_hint=(1,0.86))

        self.game=UltimateTTT()
        self.overlay=GridOverlay(self.game)

        board_area.add_widget(self.game)
        board_area.add_widget(self.overlay)

        btn_bar=BoxLayout(size_hint_y=0.1)
        undo_btn=Button(text="Undo",font_size=32,background_normal='',background_color=(0.65,0.85,1,1))
        undo_btn.bind(on_press=self.undo_move)
        reset_btn=Button(text="Restart",font_size=32,background_normal='',background_color=(1,0.75,0.75,1))
        reset_btn.bind(on_press=self.reset_game)
        help_btn=Button(text="Help",font_size=32,background_normal='',background_color=(0.8,0.95,0.8,1))  # <-- added
        help_btn.bind(on_press=self.show_help)  # <-- added

        self.status=Label(text="You are X (blue). Active board is yellow.",font_size=28,size_hint_y=0.04)

        # Add buttons to bar (Undo | Restart | Help)
        btn_bar.add_widget(undo_btn)
        btn_bar.add_widget(reset_btn)
        btn_bar.add_widget(help_btn)  # <-- added

        root.add_widget(board_area)
        root.add_widget(btn_bar)
        root.add_widget(self.status)

        board_area.bind(size=self._position_board, pos=self._position_board)
        Clock.schedule_once(lambda *_: self._position_board(board_area), 0)
        return root

    def _position_board(self, area, *args):
        side = min(area.width, area.height)
        self.game.size=(side,side)
        self.game.pos=(area.x+(area.width-side)/2.0, area.y+(area.height-side)/2.0)
        self.game.refresh_ui()
        self.overlay._sync()

    def undo_move(self,instance):
        if len(history)>=2:
            undo_last_move()
            undo_last_move()
            self.game.refresh_ui()

    def reset_game(self,instance):
        global main_board,win_board,current_player,active_board,history
        main_board=[' ']*81; win_board=[' ']*9; current_player='X'; active_board=None; history=[]
        self.game.refresh_ui(); self.status.text="You are X (blue). Active board is yellow."
        self.overlay._sync()

    # ---- NEW: in-app Help popup ----
    def show_help(self, instance=None):
        scroll = ScrollView(size_hint=(1, 1))
        lbl = Label(
            text=HELP_TEXT,
            font_size='18sp',
            halign='left',
            valign='top',
            size_hint_y=None
        )
        # Wrap text to the popup width and let it grow vertically
        lbl.text_size = (Window.width * 0.8, None)
        lbl.bind(texture_size=lambda widget, size: setattr(lbl, 'height', size[1]))
        scroll.add_widget(lbl)

        Popup(
            title="How to Play",
            content=scroll,
            size_hint=(0.9, 0.9)
        ).open()

if __name__=="__main__":
    UltimateTTTApp().run()