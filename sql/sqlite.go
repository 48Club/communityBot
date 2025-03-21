package sql

import (
	"sync"
	"time"

	"github.com/google/uuid"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

type User struct {
	ID         uint64  `gorm:"primaryKey"`
	TelegramID int64   `gorm:"unique;not null"`
	Address    *string `gorm:"unique;size:100;"`
	UUID       *string `gorm:"unique;size:36;"`    // UUID for sign msg
	EndTime    int64   `gorm:"not null;default:0"` // sign must be after this time
}

var (
	db *gorm.DB
	mu sync.Mutex
)

func init() {
	var err error
	db, err = gorm.Open(sqlite.Open("48club.db"), &gorm.Config{})
	if err != nil {
		panic(err)
	}

	err = db.AutoMigrate(&User{})
	if err != nil {
		panic(err)
	}
}

func Update(user *User) error {
	mu.Lock()
	defer mu.Unlock()
	return db.Save(&user).Error
}

func AddUser(telegramID int64) error {
	user := User{TelegramID: telegramID}
	// _ = genUUID(&user)
	mu.Lock()
	defer mu.Unlock()
	return db.Create(&user).Error
}

func genUUID(u *User) string {
	uid := uuid.New().String()
	u.UUID = &uid                         // update UUID
	u.EndTime = time.Now().Unix() + 60*60 // 1 hour
	return uid
}

func GetNewSignUUID(u User) (string, error) {
	mu.Lock()
	defer mu.Unlock()
	uid := genUUID(&u)
	return uid, db.Save(&u).Error
}

func GetUser(telegramID int64) (User, error) {
	user := User{TelegramID: telegramID}

	err := db.Where(&user).First(&user).Error

	if err != nil {
		if err == gorm.ErrRecordNotFound {
			err = nil
		}
	}
	return user, err
}
