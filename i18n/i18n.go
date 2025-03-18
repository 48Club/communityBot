package i18n

import (
	"github.com/BurntSushi/toml"
	"github.com/gin-gonic/gin"
	"github.com/nicksnyder/go-i18n/v2/i18n"
	"golang.org/x/text/language"
)

type I18nBundle struct {
	*i18n.Bundle
}

var Bundle *I18nBundle

func init() {
	bundle := i18n.NewBundle(language.SimplifiedChinese)
	bundle.RegisterUnmarshalFunc("toml", toml.Unmarshal)
	bundle.MustLoadMessageFile("i18n.zh-Hans.toml")
	bundle.MustLoadMessageFile("i18n.en.toml")

	Bundle = &I18nBundle{bundle}
}

func (b *I18nBundle) Localize(id string, data gin.H, lang ...string) string {
	localizer := i18n.NewLocalizer(b.Bundle, lang...)
	return localizer.MustLocalize(&i18n.LocalizeConfig{
		DefaultMessage: &i18n.Message{
			ID: id,
		},
		TemplateData: data,
	})
}
