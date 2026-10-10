package PKG

// Weapons scripted for generated maps (rules/WEAPONS.md). OpenNox runs this from the map's folder with behaviours.go.
//
// HarpoonStaff turns one named staff into a harpoon thrower. The staff is a Lesser Fireball staff, whose USE line
// (thing.bin: "WandUse 20 Fireball 3.0 SINGLE_SHOT SmallFireballWand 10") fires a Fireball. While the host player holds
// it, each fireball it fires becomes a harpoon bolt flying the same way, faster. A creature the bolt strikes is wounded
// and reeled in toward the player.
//
// The game's own harpoon (the warrior's ability) keeps its rope and target on the player's update data, which no script
// can reach. A HarpoonBolt the script owned would tether its target for good, and one owned by a creature would panic
// the server. So this bolt is ownerless and does not collide, and the script flies it, strikes and reels.

import (
	"math"

	"github.com/noxworld-dev/noxscript/ns/v4"
	"github.com/noxworld-dev/noxscript/ns/v4/class"
	"github.com/noxworld-dev/noxscript/ns/v4/damage"
	"github.com/noxworld-dev/opennox-lib/object"
)

type harpoonFlight struct {
	bolt   ns.Obj
	dx, dy float32
	dist   float32
	target ns.Obj
	reel   int
}

// HarpoonStaff: speed in pixels per frame (the game's HarpoonBolt flies 800 against the Fireball's 192), reach in
// pixels, dmg on a strike, reelFrames of pulling at `pull` force.
func HarpoonStaff(staffName string, speed, reach float32, dmg int, reelFrames int, pull float32) {
	var flights []*harpoonFlight
	living := ns.ObjCondFunc(func(o ns.Obj) bool { return o.HasClass(class.MONSTER) && o.CurrentHealth() > 0 })
	ns.OnFrame(func() {
		h := ns.GetHost()
		staff := ns.Object(staffName)
		if h != nil && staff != nil && h.HasEquipment(staff) {
			for _, fb := range ns.FindAllObjects(ns.HasTypeName{"Fireball"}) {
				if !fb.HasOwner(h) {
					continue
				}
				// the staff fires from just in front of its wielder, along the way it faces: that is the way to throw
				// (OpenNox 1.9's NoxScript 4.16 has no Vel())
				fp, hp := fb.Pos(), h.Pos()
				v := ns.Ptf(fp.X-hp.X, fp.Y-hp.Y)
				l := float32(math.Hypot(float64(v.X), float64(v.Y)))
				if l == 0 {
					continue
				}
				b := ns.CreateObject("HarpoonBolt", fb)
				fb.Delete()
				if b == nil {
					continue
				}
				b.FlagsEnable(object.FlagNoCollide)
				dx, dy := v.X/l, v.Y/l
				b.LookWithAngle(int(math.Atan2(float64(dy), float64(dx))/(2*math.Pi)*256) & 255)
				flights = append(flights, &harpoonFlight{bolt: b, dx: dx, dy: dy})
			}
		}
		alive := flights[:0]
		for _, f := range flights {
			if f.target == nil {
				p := f.bolt.Pos()
				f.bolt.SetPos(ns.Ptf(p.X+f.dx*speed, p.Y+f.dy*speed))
				f.dist += speed
				hit := ns.FindClosestObject(f.bolt, ns.InCirclef{Center: f.bolt, R: 22}, living)
				if hit != nil {
					if h != nil {
						hit.Damage(h, dmg, damage.IMPALE)
					}
					f.target, f.reel = hit, reelFrames
				} else if f.dist > reach || ns.FindClosestWall(f.bolt, ns.InCirclef{Center: f.bolt, R: 14}) != nil {
					f.bolt.Delete()
					continue
				}
			} else {
				if f.reel <= 0 || h == nil || f.target.CurrentHealth() <= 0 {
					f.bolt.Delete()
					continue
				}
				f.reel--
				f.bolt.SetPos(f.target.Pos())
				// PushTo pushes AWAY from the point for a positive force (OpenNox server/object.go Push: obj.Pos() - p),
				// whatever the ns doc says: a negative force reels the creature in toward the wielder
				f.target.PushTo(h, -pull)
			}
			alive = append(alive, f)
		}
		flights = alive
	})
}
