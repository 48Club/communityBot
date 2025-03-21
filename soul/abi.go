package soul

import (
	"strings"

	"github.com/ethereum/go-ethereum/accounts/abi"
)

func getAbi() *abi.ABI {
	parsed, err := abi.JSON(strings.NewReader(`[{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]`))
	if err != nil {
		panic(err)
	}
	return &parsed
}
