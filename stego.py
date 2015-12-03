import sys
import Image  # python image library
from Crypto import Random  # PyCrypto randomizer library
from Crypto.Cipher import AES  # PyCrypto AES encryption library
import binascii
import math

"""
Distributed Steganography

Only embeds a single secret into a single cover file (PNG) for now.

Todo:
-Function to partition the secret so that it can be distributed among many cover files
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
    if cover_image.mode != "RGB":  # convert to RGB mode
        cover_image = cover_image.convert("RGB")

    image_pix = cover_image.load()  # get a 2d array of pixels, each element is a tuple (r,g,b)
    width = cover_image.size[0]
    height = cover_image.size[1]
    stego_image = Image.new("RGB", (width, height))  # create output image
    stego_pix = stego_image.load()

    b = message_encode(secret)

    # check to see if the secret can fit, only in the two LSB of every pixel R value.
    # We can also try the LSB of the G and B values as well, but its only R for now
    if len(b) > width * height * 2:
        print("cover image too small to embed secret: secret: " + str(len(b)) + " bits" + " cover: " + str(
            width * height * 2) + " bits")
        exit()

    s_length = '{0:032b}'.format(len(b))
    count1 = 0
    count2 = 0
    for i in range(0, width):
        for j in range(0, height):
            if 0 <= count1 < 32:  # this embeds the size of the secret into the first 32 bits
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary
                b_value[6] = str(s_length[count1])
                b_value[7] = str(s_length[count1 + 1])
                stego_pix[i, j] = (int(''.join(b_value), 2), image_pix[i, j][1], image_pix[i, j][2])
                count1 += 2
            elif 0 <= count2 < len(b):
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary

                # Add to the LSB
                b_value[6] = str(b[count2])
                b_value[7] = str(b[count2 + 1])

                stego_pix[i, j] = (int(''.join(b_value), 2), image_pix[i, j][1], image_pix[i, j][2])
                count2 += 2

            else:
                stego_pix[i, j] = (image_pix[i, j][0], image_pix[i, j][1], image_pix[i, j][2])

    stego_image.save("output.png")


def recover(stego_file):  # takes a stego file and recovers the secret from it
    stego_image = Image.open(stego_file)
    image_pix = stego_image.load()
    width = stego_image.size[0]
    height = stego_image.size[1]

    output = []
    s_length = []

    count1 = 0
    count2 = 0

    # get the length of the secret from the first 32 bits
    for i in range(0, width):
        for j in range(0, height):
            if 0 <= count1 < 32:
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary
                # take the 2 LSB of every pixel as part of the length
                s_length.append(int(b_value[6]))
                s_length.append(int(b_value[7]))
                count1 += 2

            else:
                break

    s_length_int = int(''.join(str(x) for x in s_length), 2)
    # print(s_length_int)
    for i in range(0, width):
        for j in range(0, height):
            if 32 <= count2 < s_length_int + 32:
                p_value = image_pix[i, j][0]
                b_value = list('{0:08b}'.format(p_value))  # convert pixel value to binary

                # take the 2 LSB of every pixel as part of the secret
                output.append(int(b_value[6]))
                output.append(int(b_value[7]))
                count2 += 2
            else:
                count2 += 2

    return message_decode(output)  # return the recovered secret


def encrypt(message):
    key = generate_key()  # creates a cryptographically secure random key of 128 bits
    message += b"\0" * (
    AES.block_size - len(message) % AES.block_size)  # pads the message with null characters
    iv = Random.new().read(AES.block_size)  # initialization vector of size AES.block_size = 16
    cipher = AES.new(key, AES.MODE_CFB, iv)  # the cipher object which defines how to encrypt data
    cipher_message = iv + cipher.encrypt(message)  # appends the init vector and the scrambled message
    return cipher_message


def decrypt(cipher_message, key):
    iv = cipher_message[:AES.block_size]  # recovers the init vector from the front of the cipher_message
    cipher = AES.new(key, AES.MODE_CFB, iv)  # reconstructs the cipher
    message = cipher.decrypt(cipher_message[AES.block_size:])  # decrypts to reveal the padded message
    return message.rstrip(b"\0")  # strips the trailing null characters used for padding


def generate_key():
    key = Random.get_random_bytes(16)  # creates a cryptographically secure random key of 128 bits

    print "This is the random key assigned to your message, it must be used to decrypt your message."
    print "key: " + binascii.hexlify(key)
    return key


def split_string(input_string, num_splits):
    temp = []
    if num_splits <= 0:
        print "Error: non-positive number of splits"
        return temp
    if len(input_string) < num_splits:
        print "There are more cover files than secret length"
        return temp
    else:
        # int(math.ceil(float(len(input))/float(num_splits)))
        block = len(input_string)/num_splits
        for i in range(0, num_splits):
            block_start = i * block
            block_end = i * block + block
            if i == num_splits - 1:
                temp.append(input_string[block_start:])
            else:
                temp.append(input_string[block_start:block_end])
    print temp
    return temp


def main():
    print "Distributed Stego System"
    secret = ""
    mode = ""
    fileorstring = ""
    file_count = 1
    files = []

    split_string("this is a long string", 10)

    while True:
        mode = raw_input("Operation mode (encode/decode): ")
        if mode == "encode" or mode == "decode":
            break

    while True:
        fileorstring = raw_input("Secret Type (string/file): ")
        if fileorstring == "string" or fileorstring == "file":
            break

    print "Please enter the names of the files to " + mode + ". When finished enter \"done\"."
    while True:
        temp = raw_input("Enter the name file " + str(file_count) + ": ")

        if temp == "done":
            break

        files.append(temp)
        file_count += 1

    if mode == "encode":
        if fileorstring == "string":
            secret = raw_input("Enter the secret string: ")
            secret = encrypt(secret)
        else:
            f_path = raw_input("Enter the secret file's name: ")
            f = open(f_path, "rb")
            secret = f.read()
            secret = encrypt(secret)





















    # if len(sys.argv) < 3:  # check if there are at least two arguments
    #     usage()
    #
    # if sys.argv[1] == "-e":
    #     # embed secret into file
    #     print "Embedding secret..."
    #
    #     if sys.argv[3] == "-s":
    #         secret = sys.argv[4]
    #         secret = encrypt(secret)
    #     elif sys.argv[3] == "-f":
    #         # read file in
    #         f_path = sys.argv[4]
    #         f = open(f_path, "rb")
    #         secret = f.read()
    #         secret = encrypt(secret)
    #     else:
    #         usage()
    #
    #     embed(sys.argv[2], secret)
    #     print "Stego file is output.png"
    #     print "Finished"
    #
    # elif sys.argv[1] == "-r":
    #     # recover secret from file
    #     print "Recovering secret..."
    #     stext = recover(sys.argv[2])
    #     key = sys.argv[3]
    #     key = binascii.unhexlify(key)
    #     stext = decrypt(stext, key)
    #     print "Finished"
    #
    #     if len(sys.argv) > 4:
    #         if sys.argv[4] == "-f":
    #             fname = sys.argv[5]
    #             f = open(fname, 'wb')
    #             f.write(stext)
    #             f.close()
    #
    #         else:
    #             usage()
    #
    #     else:
    #         print "The secret is: " + stext
    #
    # else:
    #     usage()



main()
