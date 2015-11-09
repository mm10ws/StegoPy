import sys
import Image  # python image library

"""
Distributed Steganography

Only embeds a single secret into a single cover file (PNG) for now.

Todo:
-functions to encrypt/decrypt the secret (AES256)
-Way to embed how long the secret is so that it can be recovered from stego image
-Function to partition the secret so that it can be distributed among many cover files
-Embed other types of data besides text (images, sound, video files)
-Redundancy or embed a checksum


"""


def usage():
    print "Usage: [-e or -r] [name of input file]"
    exit()


def message_encode(message):  # encodes a string into an array of bits
    message_bytes = []

    for i in message:
        bts = bin(ord(i))[2:]
        bts = '00000000'[len(bts):] + bts
        message_bytes.extend([int(b) for b in bts])

    return message_bytes


def message_decode(message):  # decodes an array of bits to a string
    message_chars = []
    for i in range(len(message) / 8):
        byte = message[i * 8:8 * (i + 1)]
        message_chars.append(chr(int(''.join([str(b) for b in byte]), 2)))

    return ''.join(message_chars)


def embed(cover_file, secret):  # embed a secret into a cover file, creates a new stego image
    cover_image = Image.open(cover_file)  # open the cover image
    image_pix = cover_image.load()  # get a 2d array of pixels, each element is a tuple (r,g,b)
    width = cover_image.size[0]
    height = cover_image.size[1]
    stego_image = Image.new("RGB", (width, height))  # create output image
    stego_pix = stego_image.load()

    b = message_encode(secret)


    # check to see if the secret can fit, only in the two LSB of every pixel R value.
    # We can also try the LSB of the G and B values as well, but its only R for now
    if len(b) > width * height * 2:
        print("cover image too small to embed secret")
        exit()

    count = 0
    for i in range(0, width):
        for j in range(0, height):
            if count < len(b):
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary

                # Add to the LSB
                b_value[6] = str(b[count])
                b_value[7] = str(b[count + 1])

                stego_pix[i, j] = (int(''.join(b_value), 2), image_pix[i, j][1], image_pix[i, j][2])
                count += 2

            else:
                stego_pix[i, j] = (image_pix[i, j][0], image_pix[i, j][1], image_pix[i, j][2])

    stego_image.save("output.png")


def recover(stego_file):  # takes a stego file and recovers the secret from it
    stego_image = Image.open(stego_file)
    image_pix = stego_image.load()
    width = stego_image.size[0]
    height = stego_image.size[1]

    output = []

    count = 0
    for i in range(0, width):
        for j in range(0, height):

            if count < 128:  # find a way to figure out secret size, hardcoded for now
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary

                # take the 2 LSB of every pixel as part of the secret
                output.append(int(b_value[6]))
                output.append(int(b_value[7]))
                count += 2

    return message_decode(output)  # return the recovered secret


def main():
    print "Stego System"
    secret = "this is a secret"  # this string is 16 chars long, 1 Byte * 16 = 128 bits, This is hardcoded for now

    if len(sys.argv) < 3:  # check if there are at least two arguments
        usage()

    if sys.argv[1] == "-e":
        # embed secret into file
        print "Embedding secret..."
        embed(sys.argv[2], secret)
        print "Stego file is output.png"
        print "Finished"

    elif sys.argv[1] == "-r":
        # recover secret from file
        print "Recovering secret..."
        stext = recover(sys.argv[2])
        print "Finished"
        print "The secret is: " + stext

    else:
        usage()


main()