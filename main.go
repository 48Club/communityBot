package main

import (
	"log"
	"os"
	"time"

	"github.com/48Club/communityBot/i18n"
	"github.com/48Club/communityBot/soul"
	mapset "github.com/deckarep/golang-set/v2"
	tele "gopkg.in/telebot.v4"
)

func init() {
	pref := tele.Settings{
		Token:  os.Getenv("TOKEN"),
		Poller: &tele.LongPoller{Timeout: 10 * time.Second},
	}

	var err error
	bot, err = tele.NewBot(pref)
	if err != nil {
		log.Panic(err)
		return
	}

	groupIDs = mapset.NewSet[int64](
		-1001345282090, // @cn_48club
		-1001846893990, // test chat group
	)
}

var (
	MustLocalize = i18n.Bundle.Localize
	bot          *tele.Bot
	groupIDs     mapset.Set[int64]
)

func main() {

	// new user join group
	bot.Handle(tele.OnUserJoined, func(c tele.Context) error {
		_ = c.Delete()
		for _, user := range c.Message().UsersJoined {
			c.Send(MustLocalize("Group.OnUserJoined", getUserWhitID(&user), user.LanguageCode), tele.ModeMarkdownV2)
		}
		return nil
	})

	// user leave group
	bot.Handle(tele.OnUserLeft, func(c tele.Context) error { return c.Delete() })

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
					msg = MustLocalize("Group.NotBindWallet", getUserWhitID(c.Message().Sender), c.Sender().LanguageCode)
				} else if sp == 0 { // not enough point
					msg = MustLocalize("Group.NotEnoughPoint", getUserWhitID(c.Message().Sender), c.Sender().LanguageCode)
				}

				_ = bot.Restrict(c.Chat(), &tele.ChatMember{
					User:            user,
					Rights:          tele.Rights{CanSendMessages: false},
					RestrictedUntil: time.Now().Unix() + 3*60,
				}) // restrict user send message 3 minutes

				alertMsg, err := bot.Send(c.Chat(), msg, tele.ModeMarkdownV2)
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
