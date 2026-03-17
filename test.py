import astronomy

# current time
t = astronomy.Time.Now()

# create an observer (latitude, longitude, elevation)
observer = astronomy.Observer(0, 0, 0)

# compute Sun coordinates
sun = astronomy.Equator(
    astronomy.Body.Sun,
    t,
    observer,
    True,
    True
)

print("RA:", sun.ra)
print("DEC:", sun.dec)

const = astronomy.Constellation(sun.ra, sun.dec)

print(const.name)
print(const.symbol)
