package bot

import (
	"fmt"
	"os"
	"slices"
	"strings"
	"time"

	"github.com/48Club/communityBot/i18n"
	"github.com/48Club/communityBot/soul"
	"github.com/48Club/communityBot/sql"
	mapset "github.com/deckarep/golang-set/v2"
	"github.com/gin-gonic/gin"
	tele "gopkg.in/telebot.v4"
)

var (
	MustLocalize = i18n.Bundle.Localize
	MDv2         = tele.ModeMarkdownV2
	groupIDs     mapset.Set[int64]
	botUsername  string
)

func init() {
	groupIDs = mapset.NewSet[int64](
		-1001345282090, // @cn_48club
		-1001846893990, // test chat group
		-1001695915153, // Ian's Fans Club
	)
}

func setBotUsername(bot *tele.Bot) {
	botUsername = bot.Me.Username
}

func setCommands(bot *tele.Bot) {
	commands := []tele.Command{
		{Text: "start", Description: "Start bot"},
		{Text: "bind", Description: "Bind wallet"},
		{Text: "unbind", Description: "Unbind wallet"},
	}

	if err := bot.SetCommands(commands); err != nil {
		panic(err)
	}
}

func onUserJoined(c tele.Context) error {
	_ = c.Delete()
	var userLinks map[string][]string = make(map[string][]string)

	for _, user := range c.Message().UsersJoined {
		lang := user.LanguageCode
		userLink := getUserLinkString(&user)
		if userLinks[lang] == nil {
			userLinks[lang] = []string{userLink}
		} else {
			userLinks[lang] = append(userLinks[lang], userLink)
		}
	}

	sendWelcomeMsg := func(lang string, users []string) {
		if len(users) == 0 {
			return
		}

		replyMsg, err := c.Bot().Send(c.Chat(), MustLocalize("Group.OnUserJoined", gin.H{"Users": strings.Join(users, ", ")}, lang), MDv2)
		if err == nil {
			go func(m *tele.Message) {
				time.Sleep(3 * time.Minute)
				_ = c.Bot().Delete(m)
			}(replyMsg)
		}
	}

	for lang, users := range userLinks {
		sendWelcomeMsg(lang, users)
	}

	return nil
}

func onText(c tele.Context) error {
	if c.Chat().ID < 0 {
		return nil
	}
	if len(c.Message().Text) != 132 {
		return nil
	}
	if !strings.HasPrefix(c.Message().Text, "0x") {
		return nil
	}
	lang := c.Sender().LanguageCode
	tgID := c.Message().Sender.ID
	user, err := sql.GetUser(tgID)
	if err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}
	if user.UUID == nil {
		return nil
	}

	addr, err := getAddressFromSignature(*user.UUID, c.Message().Text)
	if err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}
	user.Address = &addr
	user.UUID = nil
	user.EndTime = 0
	if err := sql.Update(&user); err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}
	return c.Reply(MustLocalize("Chat.BindWalletSuccess", gin.H{"Wallet": addr}, lang), MDv2)
}

func bind(c tele.Context) error {
	lang := c.Sender().LanguageCode
	tgID := c.Message().Sender.ID

	user, err := sql.GetUser(tgID)
	if err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}

	if user.Address != nil {
		return c.Reply(MustLocalize("Chat.HasBindWallet", gin.H{"Wallet": user.Address}, lang), append([]any{MDv2}, &tele.ReplyMarkup{InlineKeyboard: [][]tele.InlineButton{
			{
				{Text: MustLocalize("Chat.Click2UnBindWallet", nil, lang), URL: fmt.Sprintf("https://t.me/%s?start=unbind", botUsername)},
			},
		}})...)
	}

	return c.Reply(MustLocalize("Chat.BindWallet", nil, lang), append([]any{MDv2}, &tele.ReplyMarkup{InlineKeyboard: [][]tele.InlineButton{
		{
			// {Text: MustLocalize("Chat.BindWalletTypeA", nil, lang), Data: "@todo"},
			{Text: MustLocalize("Chat.BindWalletTypeB", nil, lang), URL: fmt.Sprintf("https://t.me/%s?start=bind-b", botUsername)},
		},
	}})...)
}

func unBind(c tele.Context) error {
	if c.Chat().ID < 0 {
		return nil
	}
	lang := c.Sender().LanguageCode
	tgID := c.Message().Sender.ID
	user, err := sql.GetUser(tgID)

	if err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}
	user.Address = nil
	if err := sql.Update(&user); err != nil {
		return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
	}
	return c.Reply(MustLocalize("Chat.UnBindWalletSuccess", nil, lang), MDv2)
}

func start(c tele.Context) error {
	if c.Chat().ID < 0 {
		return nil
	}

	lang := c.Sender().LanguageCode
	tgID := c.Message().Sender.ID

	if slices.Equal(c.Args(), []string{"bind"}) {
		return bind(c)
	}

	if slices.Equal(c.Args(), []string{"bind-b"}) {
		user, err := sql.GetUser(tgID)
		if err != nil {
			return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
		}

		uuid, err := sql.GetNewSignUUID(user)
		if err != nil {
			return c.Reply(MustLocalize("Chat.Error", gin.H{"Error": err.Error()}, lang))
		}

		return c.Reply(MustLocalize("Chat.BindWalletTypeBGuide", gin.H{"Sign": uuid}, lang), MDv2)
	}
	if slices.Equal(c.Args(), []string{"unbind"}) {
		return unBind(c)
	}

	return c.Reply(MustLocalize("Chat.Start", nil, lang), MDv2)
}

func NewBot() *tele.Bot {
	pref := tele.Settings{
		Token:  os.Getenv("TOKEN"),
		Poller: &tele.LongPoller{Timeout: 10 * time.Second},
	}

	b, err := tele.NewBot(pref)
	if err != nil {
		panic(err)
	}

	setBotUsername(b)
	setCommands(b)
	return b
}
func AddHandler(bot *tele.Bot) {

	// new user join group
	bot.Handle(tele.OnUserJoined, onUserJoined)

	// user leave group
	bot.Handle(tele.OnUserLeft, func(c tele.Context) error {
		return c.Delete()
	})
	// user send message

	bot.Handle(tele.OnText, onText)

	bot.Handle("/unbind", unBind)
	bot.Handle("/bind", bind)

	bot.Handle("/start", start)
}

func Start(bot *tele.Bot) {
	stop := make(chan struct{})

	go bot.Poller.Poll(bot, bot.Updates, stop)

	for {
		upd := <-bot.Updates
		c := bot.NewContext(upd)
		m := c.Message()
		sikpCheck := false
		if m != nil {
			if m.Chat != nil && m.Chat.ID < 0 {
				if !groupIDs.Contains(m.Chat.ID) {
					continue
				}
				sikpCheck = m.Sender.ID == 777000 || m.Chat.ID > 0 || m.UserLeft != nil || len(m.UsersJoined) > 0 || m.UserJoined != nil
			}

		}

		bot.ProcessContext(c)
		if sikpCheck {
			continue
		}

		go allMsgCheck(c)
	}
}

func allMsgCheck(c tele.Context) {
	user := c.Sender()
	userSp := soul.CheckSoulPoint(user)
	if userSp == soul.SP_VALID { // check soul point
		return
	}

	_ = c.Delete()
	var msg string
	opt := []any{MDv2}
	lang := c.Sender().LanguageCode

	switch userSp {
	case soul.SP_NOT_BIND: // not bind account
		msg = MustLocalize("Group.NotBindWallet", getUserLinkStruct(c.Message().Sender), lang)
		opt = append(opt, &tele.ReplyMarkup{InlineKeyboard: [][]tele.InlineButton{
			{
				{Text: MustLocalize("Group.BindWallet", nil, lang), URL: fmt.Sprintf("https://t.me/%s?start=bind", botUsername)},
			},
		}})
	case soul.SP_NOT_ENOUGH: // not enough point
		msg = MustLocalize("Group.NotEnoughPoint", getUserLinkStruct(c.Message().Sender), lang)
	}

	// restrict user send message 3 minutes
	_ = c.Bot().Restrict(c.Chat(), &tele.ChatMember{
		User:            user,
		Rights:          tele.Rights{CanSendMessages: false},
		RestrictedUntil: time.Now().Unix() + 3*60,
	})

	alertMsg, err := c.Bot().Send(c.Chat(), msg, opt...)
	if err == nil {
		go func(m *tele.Message) {
			time.Sleep(15 * time.Second)
			_ = c.Bot().Delete(m)
		}(alertMsg)
	}
}
