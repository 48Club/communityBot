package bot

import (
	"strings"
	"time"

	"github.com/48Club/communityBot/i18n"
	"github.com/48Club/communityBot/soul"
	mapset "github.com/deckarep/golang-set/v2"
	"github.com/gin-gonic/gin"
	tele "gopkg.in/telebot.v4"
)

var (
	MustLocalize = i18n.Bundle.Localize
	groupIDs     mapset.Set[int64]
	MDv2         = tele.ModeMarkdownV2
)

func init() {
	groupIDs = mapset.NewSet[int64](
		-1001345282090, // @cn_48club
		-1001846893990, // test chat group
	)
}
func AddHandler(bot *tele.Bot) {
	// new user join group
	bot.Handle(tele.OnUserJoined, func(c tele.Context) error {
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
			msg := strings.Join(users, ", ")
			replyMsg, err := bot.Send(c.Chat(), MustLocalize("Group.OnUserJoined", gin.H{"Users": msg}, lang), MDv2)
			if err == nil {
				go func(m *tele.Message) {
					time.Sleep(3 * time.Minute)
					_ = bot.Delete(m)
				}(replyMsg)
			}
		}

		for lang, users := range userLinks {
			sendWelcomeMsg(lang, users)
		}

		return nil
	})

	// user leave group
	bot.Handle(tele.OnUserLeft, func(c tele.Context) error { return c.Delete() })
}

func Start(bot *tele.Bot) {
	stop := make(chan struct{})

	go bot.Poller.Poll(bot, bot.Updates, stop)

	for {
		upd := <-bot.Updates
		if upd.Message != nil && upd.Message.Chat != nil {
			if chatID := upd.Message.Chat.ID; chatID < 0 && !groupIDs.Contains(chatID) {
				// check chatID, if not in groupIDs, skip
				continue
			}
		}
		c := bot.NewContext(upd)
		m := upd.Message
		if m.Chat != nil && m.Chat.ID < 0 && m.UsersJoined == nil && m.UserJoined == nil && m.UserLeft == nil { // not join or leave group
			user := m.Sender
			if sp := soul.CheckSoulPoint(user); sp <= 0 { // check soul point
				_ = c.Delete()
				var msg string
				if sp == -1 { // not bind account
					// TODO: add bind account button
					msg = MustLocalize("Group.NotBindWallet", getUserLinkStruct(c.Message().Sender), c.Sender().LanguageCode)
				} else if sp == 0 { // not enough point
					msg = MustLocalize("Group.NotEnoughPoint", getUserLinkStruct(c.Message().Sender), c.Sender().LanguageCode)
				}

				_ = bot.Restrict(c.Chat(), &tele.ChatMember{
					User:            user,
					Rights:          tele.Rights{CanSendMessages: false},
					RestrictedUntil: time.Now().Unix() + 3*60,
				}) // restrict user send message 3 minutes

				alertMsg, err := bot.Send(c.Chat(), msg, MDv2)
				if err == nil {
					go func(m *tele.Message) {
						time.Sleep(3 * time.Minute)
						_ = bot.Delete(m)
					}(alertMsg)
				}
				continue
			}
		}

		bot.ProcessContext(c)
	}
}
