package main

import (
	"github.com/48Club/communityBot/bot"
)

func main() {
	b := bot.NewBot()

	bot.AddHandler(b)
	bot.Start(b)
}
